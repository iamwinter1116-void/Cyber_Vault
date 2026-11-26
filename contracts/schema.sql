-- ABHEDYA canonical database contract, version 1.
-- FROZEN after gate G0. Change only through a change request (docs/09_BUG_JOURNAL.md, section CR).
-- Target: PostgreSQL 16 or newer. Applied once by the owner role at first start (db/init).
-- Runtime services never connect as the owner. They use abh_api, abh_runner, abh_notary.

-- ---------------------------------------------------------------- roles
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'abh_api')    THEN CREATE ROLE abh_api    LOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'abh_runner') THEN CREATE ROLE abh_runner LOGIN; END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'abh_notary') THEN CREATE ROLE abh_notary LOGIN; END IF;
END $$;
-- Passwords are set at deploy time from secrets (ALTER ROLE ... PASSWORD), never in this file.

-- ---------------------------------------------------------------- tenancy and identity
CREATE TABLE team (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name             text NOT NULL UNIQUE CHECK (name ~ '^[a-z0-9-]{3,32}$'),
  quota_envs       int  NOT NULL DEFAULT 4    CHECK (quota_envs >= 0),
  quota_cpu_millis int  NOT NULL DEFAULT 2000 CHECK (quota_cpu_millis >= 0),
  quota_mem_mb     int  NOT NULL DEFAULT 2048 CHECK (quota_mem_mb >= 0),
  quota_storage_mb int  NOT NULL DEFAULT 1024 CHECK (quota_storage_mb >= 0),
  created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_user (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text NOT NULL UNIQUE CHECK (email = lower(email) AND length(email) BETWEEN 3 AND 254),
  password_hash text NOT NULL,                      -- Argon2id PHC string, never anything else
  role          text NOT NULL CHECK (role IN ('admin', 'team_lead', 'analyst', 'auditor')),
  team_id       uuid REFERENCES team(id),
  totp_secret   text,                               -- stretch S1; NULL means not enrolled
  disabled      boolean NOT NULL DEFAULT false,
  failed_logins int NOT NULL DEFAULT 0,
  locked_until  timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  -- admin and auditor are platform roles without a team; team_lead and analyst always have one
  CHECK ((role IN ('admin', 'auditor')) = (team_id IS NULL))
);

CREATE TABLE session (
  token_sha256 text PRIMARY KEY CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),  -- raw token is never stored
  user_id      uuid NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  csrf_token   text NOT NULL,
  ip           text NOT NULL,
  user_agent   text NOT NULL DEFAULT '',
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL
);
CREATE INDEX session_user_idx ON session (user_id);

-- ---------------------------------------------------------------- environments (reconciler pattern)
-- The API writes desired_state. Only the runner writes observed_state, isolation_tier, failure_reason.
CREATE TABLE env (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id        uuid NOT NULL REFERENCES team(id),
  owner_id       uuid NOT NULL REFERENCES app_user(id),
  name           text NOT NULL CHECK (name ~ '^[a-z0-9-]{3,32}$'),
  template       text NOT NULL CHECK (template IN ('app-target', 'file-analysis', 'ai-redteam')),
  size           text NOT NULL CHECK (size IN ('S', 'M', 'L')),
  cpu_millis     int  NOT NULL CHECK (cpu_millis > 0),
  mem_mb         int  NOT NULL CHECK (mem_mb > 0),
  storage_mb     int  NOT NULL CHECK (storage_mb > 0),
  pids_limit     int  NOT NULL CHECK (pids_limit > 0),
  desired_state  text NOT NULL DEFAULT 'running'
                 CHECK (desired_state IN ('running', 'stopped', 'destroyed')),
  observed_state text NOT NULL DEFAULT 'requested'
                 CHECK (observed_state IN ('requested', 'provisioning', 'running', 'stopped', 'destroyed', 'failed')),
  isolation_tier text NOT NULL DEFAULT '' CHECK (isolation_tier IN ('', 'gvisor', 'runc-hardened')),
  failure_reason text NOT NULL DEFAULT '',
  expires_at     timestamptz NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
-- a team may reuse a name once the old environment is destroyed
CREATE UNIQUE INDEX env_team_name_live ON env (team_id, name) WHERE observed_state <> 'destroyed';
CREATE INDEX env_reconcile_idx ON env (observed_state, desired_state);

-- ---------------------------------------------------------------- jobs (exec, file analysis, AI scan)
-- input and result shapes per kind are fixed in docs/04_CONTRACTS.md section 5.
CREATE TABLE job (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         text NOT NULL CHECK (kind IN ('exec', 'file_analysis', 'ai_scan')),
  env_id       uuid NOT NULL REFERENCES env(id),
  team_id      uuid NOT NULL REFERENCES team(id),
  requested_by uuid NOT NULL REFERENCES app_user(id),
  input        jsonb NOT NULL,
  status       text NOT NULL DEFAULT 'queued'
               CHECK (status IN ('queued', 'running', 'done', 'timeout', 'error')),
  result       jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at   timestamptz NOT NULL DEFAULT now(),
  started_at   timestamptz,
  finished_at  timestamptz
);
CREATE INDEX job_queue_idx ON job (status, created_at);
CREATE INDEX job_team_idx  ON job (team_id, created_at DESC);

-- ---------------------------------------------------------------- monitoring
CREATE TABLE metric_sample (
  env_id       uuid NOT NULL REFERENCES env(id),
  ts           timestamptz NOT NULL DEFAULT now(),
  cpu_pct      real   NOT NULL,   -- percent of the environment's own CPU limit, 0..100+
  mem_mb       real   NOT NULL,
  storage_mb   real   NOT NULL,
  pids         int    NOT NULL,
  net_rx_bytes bigint NOT NULL,
  net_tx_bytes bigint NOT NULL,
  PRIMARY KEY (env_id, ts)
);

CREATE TABLE activity_event (
  id       bigserial PRIMARY KEY,
  ts       timestamptz NOT NULL DEFAULT now(),
  team_id  uuid REFERENCES team(id),   -- NULL means platform-wide, visible to admin and auditor only
  env_id   uuid REFERENCES env(id),
  severity text NOT NULL CHECK (severity IN ('info', 'warn', 'critical')),
  kind     text NOT NULL,              -- closed list in docs/04_CONTRACTS.md section 6
  message  text NOT NULL,
  data     jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX activity_team_idx ON activity_event (team_id, id DESC);

CREATE FUNCTION activity_notify() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify('abh_activity', NEW.id::text);
  RETURN NEW;
END $$;
CREATE TRIGGER activity_notify_trg AFTER INSERT ON activity_event
  FOR EACH ROW EXECUTE FUNCTION activity_notify();

-- ---------------------------------------------------------------- audit ledger (spec: abhedya-audit-v1)
-- Every column except hash is part of the hashed record body. See docs/04_CONTRACTS.md section 7.
CREATE TABLE audit_log (
  v           int NOT NULL DEFAULT 1 CHECK (v = 1),   -- record format version, part of the hashed body
  seq         bigint PRIMARY KEY CHECK (seq >= 1),
  ts          text NOT NULL CHECK (ts ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$'),
  actor_type  text NOT NULL CHECK (actor_type IN ('user', 'service', 'system')),
  actor_id    text NOT NULL,
  actor_role  text NOT NULL,
  team_id     text NOT NULL,           -- '' when not team-scoped
  action      text NOT NULL,           -- closed list in docs/04_CONTRACTS.md section 7.6
  target_type text NOT NULL,
  target_id   text NOT NULL,
  outcome     text NOT NULL CHECK (outcome IN ('success', 'denied', 'error')),
  ip          text NOT NULL,
  request_id  text NOT NULL,
  detail      jsonb NOT NULL DEFAULT '{}'::jsonb,
  prev_hash   text NOT NULL CHECK (prev_hash ~ '^[0-9a-f]{64}$'),
  hash        text NOT NULL UNIQUE CHECK (hash ~ '^[0-9a-f]{64}$')
);
CREATE INDEX audit_team_idx   ON audit_log (team_id, seq DESC);
CREATE INDEX audit_action_idx ON audit_log (action, seq DESC);

-- Prevention layer. Detection does not depend on it: a superuser can disable these triggers,
-- and the hash chain plus signed checkpoints must still expose the change.
CREATE FUNCTION audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only (% blocked)', TG_OP;
END $$;
CREATE TRIGGER audit_no_update_delete BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_immutable();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit_log
  FOR EACH STATEMENT EXECUTE FUNCTION audit_immutable();

CREATE FUNCTION audit_notify() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_notify('abh_audit', NEW.seq::text);
  RETURN NEW;
END $$;
CREATE TRIGGER audit_notify_trg AFTER INSERT ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_notify();

CREATE TABLE audit_checkpoint (
  tree_size  bigint PRIMARY KEY CHECK (tree_size >= 1),
  root_hash  text NOT NULL CHECK (root_hash ~ '^[0-9a-f]{64}$'),
  head_hash  text NOT NULL CHECK (head_hash ~ '^[0-9a-f]{64}$'),
  ts         text NOT NULL,
  log_id     text NOT NULL CHECK (log_id ~ '^[0-9a-f]{16}$'),
  signature  text NOT NULL CHECK (signature ~ '^[0-9a-f]{128}$'),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- least-privilege grants
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;

GRANT SELECT, INSERT, UPDATE, DELETE ON team, app_user, session TO abh_api;
GRANT SELECT, INSERT, UPDATE ON env, job TO abh_api;
GRANT SELECT ON metric_sample, audit_checkpoint TO abh_api;
GRANT SELECT, INSERT ON activity_event, audit_log TO abh_api;

GRANT SELECT ON team, app_user TO abh_runner;
GRANT SELECT, UPDATE ON env, job TO abh_runner;
GRANT SELECT, INSERT, DELETE ON metric_sample TO abh_runner;
GRANT SELECT, INSERT ON activity_event, audit_log TO abh_runner;

GRANT SELECT, INSERT ON audit_log, audit_checkpoint, activity_event TO abh_notary;

GRANT USAGE ON SEQUENCE activity_event_id_seq TO abh_api, abh_runner, abh_notary;
-- No runtime role holds UPDATE, DELETE or TRUNCATE on audit_log or audit_checkpoint.

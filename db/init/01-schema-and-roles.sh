#!/bin/sh
# Runs once in the official PostgreSQL image during initial database creation.
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

for role in abh_api abh_runner abh_notary; do
  [ -s "/run/secrets/$role" ] || {
    printf 'missing password file for %s\n' "$role" >&2
    exit 1
  }
done

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /contracts/schema.sql

psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -v api_password="$(cat /run/secrets/abh_api)" \
  -v runner_password="$(cat /run/secrets/abh_runner)" \
  -v notary_password="$(cat /run/secrets/abh_notary)" <<'SQL'
ALTER ROLE abh_api PASSWORD :'api_password';
ALTER ROLE abh_runner PASSWORD :'runner_password';
ALTER ROLE abh_notary PASSWORD :'notary_password';
SQL

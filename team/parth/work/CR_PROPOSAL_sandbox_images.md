# Change-request PROPOSAL · base images, packages, probes and target app (role B, Parth)

Status: PROPOSAL for the four-person CR process (CLAUDE.md rule 8; docs/03_CONTEXT.md section 6 says "Anything
else needs a change request"). NOT approved. Nothing has been pulled, built or installed. Every fact below was
read on 2026-11-26 from the named registry; anything not read is marked UNVERIFIED.

## 1. Scope
In scope: `app-target` images (`target`, `toolbox`), the `detonator` base for file-analysis, the probe scripts,
the in-repo vulnerable app, and the runner's own service image.
Out of scope: `analyzer` (yara-x, task B6, waits on the runner budget decision) and `ai-redteam` (task B7,
blocked by the O9 change request). Henil's `api`/`notary` and Manas's `proxy` images need the same kind of
decision; this proposal only notes the facts that also apply to them.

## 2. Base image (one base for every image in scope)
Proposed: Docker Official Image `library/python`, tag `3.13-slim-trixie` (Debian 13), always referenced by digest
with pull policy never (docs/04 section 8):
- image index digest `sha256:7249d5587b78209a006dc4a3b5340678f84ea729239193aa559962cd8c1fce50`
- linux/amd64 manifest `sha256:e123d49d13f666b842ae2b925bf30703910481c67c89edc0a6b42e09d2b2168d`
- read 2026-11-26T16:26Z: `GET registry-1.docker.io/v2/library/python/manifests/3.13-slim-trixie`
  (anonymous pull token from auth.docker.io), header `Docker-Content-Digest`. Tags move; the digest does not.
Why one Python base: the probes and the target app need only the Python standard library, so no extra package
manager is needed for them; one digest to review; the same base serves the runner image.
Why 3.13: every runner dependency has Linux x86_64 wheels for it (PyPI JSON, read 2026-11-26):
`psycopg-binary==3.3.9` cp310-cp315 · `PyYAML==6.0.4` cp310-cp315 · `pydantic-core==2.50.5` (pinned by
`pydantic==2.14.4`) cp310-cp315 · `pydantic-settings==2.16.3` requires Python >= 3.11. So 3.11 to 3.15 all work;
3.13 is proposed as a release with two years of fixes behind it. Alternatives for the team: any of 3.11-3.15;
`-slim-bookworm` (Debian 12).
UNVERIFIED until the Linux build: the exact tools inside the slim base (expected `sh`, coreutils `timeout`, `df`,
`stat`, `test`; `curl` expected absent; `perl` unknown). Step 7 lists them by command, not by assumption.

## 3. Packages per container
| Container | Needs (source of the need) | Proposed source |
| --- | --- | --- |
| every exec-able container | `sh`, `timeout` (B5 argv), `df` (V2/V3 storage reading, docs/08 section 4) | base image (verify, step 7) |
| `toolbox` | `curl` (Bhavya T-WL-01; B1 prompt), TCP-connect port scanner (B1 prompt), probes (B2) | `curl` from Debian trixie apt at build time, version recorded; scanner and probes in-repo Python |
| `target` | the vulnerable app (section 5) | in-repo Python, no extra package |
| `detonator` | script interpreters (docs/08 section 6), `probe_connect` (Bhavya T-WL-02 calls it in the detonation script) | base `sh` and `python3`; probes copied in |
| `runner` service | Python packages | see below |

Runner Python packages: the lock (evidence/VERSIONS.lock) has `docker==7.2.0`, `psycopg==3.3.9`,
`psycopg-binary==3.3.9`, `psycopg-pool==3.3.3`, `pydantic-settings==2.16.3`, `pyyaml==6.0.4`. Installing them
also installs packages that are neither allowlisted nor locked (from each package's PyPI `requires_dist`):
`requests`, `urllib3` (docker); `pydantic`, `python-dotenv`, `typing-inspection`, `typing-extensions`
(pydantic-settings); `pydantic-core==2.50.5`, `annotated-types` (pydantic); `typing-extensions` (psycopg-pool).
(`pywin32` and `tzdata` are Windows-only markers and do not apply to Linux images.)
Decision needed: whether transitive packages are covered by the allowlist entry of their parent or each needs an
entry. Proposal: record every installed package with exact version and PyPI sha256 in the lock, and build with
`pip install --require-hashes`, so the image contains only recorded files.

## 4. Probe language and contract
Python standard library, in `sandbox/probes/`, at most 120 lines in total (B2 prompt). Each probe prints one JSON
object on its last stdout line in Python `json.dumps` default style; exit 0 when the probe ran. Contract agreed
with Bhavya (team/parth/work/HANDOFFS.md, 2075dbf, plus the later additive correction):
`probe_connect <host> <port> <timeout_s>`, `probe_icmp <ip> <timeout_s>` (tries an unprivileged ICMP datagram
socket first; reports `sent`), `probe_dns <name> <timeout_s>`, `probe_env` (env var names, `mounts`,
`cap_eff`, uid, gid, kernel release), `probe_write <path>`, plus `mem_hog`, `cpu_burn`, `fork_bomb`, `disk_fill`.
Whether unprivileged ICMP works under gVisor with cap_drop ALL is UNVERIFIED (tested in step 7).

## 5. Vulnerable target
In-repo, Python standard library `http.server`, at most 60 lines (B1 prompt), port 8080 (Bhavya T-WL-01 requests
`http://target:8080/`), running as uid 1000 with a read-only root. Proposed weaknesses, for the team to accept or
change: command injection in a "ping" form, and a path-traversal file viewer. The `flag_env` file lives in
`/workspace` and is written through the API (docs/08 section 12), never baked into an image. No third-party
vulnerable image, so no further dependency.

## 6. sandbox/ budget (docs/05: 450 lines for Dockerfiles, vulnerable app, model stub, rules, probes)
Estimates, not measurements (my B5 estimate was wrong by 2x, so treat these as upper-bound guesses): probes <= 120,
target app <= 60, port scanner ~25, Dockerfiles ~40, template YAML ~30. The analyzer rules (B6) and the model
target (B7) also draw on this budget later.

## 7. Verification steps (Linux demo host, in Manas's test window; nothing runs on Windows/Docker Desktop)
1. Build each image `FROM python:3.13-slim-trixie@sha256:7249d558...1fce50`; record `docker image inspect`
   `Id` and `RepoDigests` into the template's `template.yaml` and evidence.
2. Record contents: `docker run --rm --read-only --user 1000:1000 --runtime=runsc <image> sh -c
   'for t in sh timeout df stat test curl python3 perl; do command -v $t || echo MISSING $t; done'`, and
   `dpkg-query -W` for any apt package added.
3. Each probe once inside a sandbox, output pasted; then B2's own isolation table (B2 done-when).
4. Then the existing tests in order: T-ISO-01..07, T-RES-01..06, T-WL-01, T-E2E-01, and B5's pending exec checks
   (hostile command, `sleep 70` -> timeout, 200000-byte output -> truncated).

## 8. Decisions requested (all four approvals)
1. Base image and tag (section 2). 2. Transitive-package rule and hash-pinned install (section 3). 3. `curl` from
Debian apt in `toolbox`. 4. Python probes (section 4). 5. The target app and its weaknesses (section 5).

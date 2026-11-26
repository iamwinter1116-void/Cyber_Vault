# Change-request draft · sandbox base images and packages (for the four-person CR process)

Status: DRAFT by Parth (role B) for team decision. Not approved. No image has been built or pulled.

## What
docs/03_CONTEXT.md section 6 allowlists sandbox images `yara-x` and `garak` only and says "Anything else
needs a change request." Building the B2/B4 sandbox images (app-target `toolbox` and `target`, file-analysis
`analyzer` and `detonator`) needs, in addition:
1. A base OS image for each container (to be pinned by sha256 digest, pull policy never, docs/04 section 8).
2. Packages inside them: `sh` and `timeout` in every container that runs jobs (B5 uses
   `timeout -s KILL 60 sh -c <command>`); `curl` in `toolbox` (Bhavya's T-WL-01 calls it); `df` for V2/V3
   storage readings (docs/08 section 4); an interpreter for the probe scripts; script interpreters in
   `detonator` (docs/08 section 6).
3. The vulnerable application served by `target`: the docs name the template but not the application.

## Why
G1 needs an S `app-target` environment to reach `running` on gVisor. That needs sandbox/templates with real
image digests, which need real images. Without a decision none of T-ISO-01..07, T-RES-*, T-WL-*, T-E2E-01 can run.

## Who is affected
Parth (images, probes, templates), Bhavya (security/workload tests call the probes and curl), Manas (image
build on the Linux host, VERSIONS.lock/evidence of image digests), Henil (none expected).

## Questions to decide (no option is pre-selected)
- Which base image(s), from which official publisher, recorded how in evidence/VERSIONS.lock?
- Probe language: Python standard library (needs a Python base) or POSIX sh only?
- Which in-repo vulnerable application for `target` (sandbox/ budget is 450 lines including it)?
- Where images are built (Manas's Linux host) and who records the resulting digests.

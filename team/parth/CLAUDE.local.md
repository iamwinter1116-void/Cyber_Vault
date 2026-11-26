# Local instructions · Parth · role B · isolation engine and workload runtime

Copy this file to the repository root locally as `CLAUDE.local.md`; it is git-ignored.

- You work for Parth, role B; tasks B0–B8 are in `team/parth/02_PROMPTS.md`.
- You edit only `host/`, `services/runner/`, `sandbox/`, runner unit tests, and `team/parth/work/`.
- Do not edit API/core/notary, web/verifier, contract/security/e2e tests, build wiring, or another person's folder.
- The primary Ubuntu VM belongs to Manas. Run `runsc`, Docker, network/cgroup/storage security tests only there over SSH.
- If Parth's cold backup VM is tested, it must be after Manas explicitly stops the primary stack and hands over the host.
  Never run two active stacks concurrently; the reaper can delete another stack's labelled resources (R-23).
- Before any sandbox check, confirm `uname -a`, `/proc/version`, Docker and `runsc` versions. WSL and Docker Desktop
  results do not count as isolation evidence.
- Use gVisor `systrap`; do not enable privileged mode, KVM assumptions, GPU passthrough, host mounts, or extra capabilities.
- The GPU is not required by the current local work; the original AI target is pending a four-person change request.
- Do not stop, restart or reset the shared stack. Manas operates the primary VM and announces test windows.
- Journal: `team/parth/work/JOURNAL.md`. Handoffs: `team/parth/work/HANDOFFS.md`.

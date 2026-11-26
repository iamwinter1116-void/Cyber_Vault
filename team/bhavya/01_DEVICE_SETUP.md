# Bhavya · Ryzen 7 / RTX 3050 / 16 GB development setup

Use this laptop for UI, independent verifier, contract tests, security tests and evidence authoring. Do not operate a
Docker stack here; Manas owns the primary Ubuntu VM and Parth owns sandbox runtime code.

## 1. WSL 2 setup

1. Verify the installed Windows version and enable WSL 2/Ubuntu using Microsoft's official current instructions.
2. Clone the repository in the Linux filesystem, for example `~/abhedya`, never under `/mnt/c` for Linux tools.
3. Copy `team/bhavya/CLAUDE.local.md` to the repository root as local `CLAUDE.local.md`; keep it untracked/ignored.
4. Install the project-approved Node and Python tools only after checking the dependency allowlist and registry.
5. Use `make check-fast` for local checks after Manas's M1 build scaffold is merged to `integration`.
6. Run the standalone verifier and vector tests locally. Do not start Docker or claim sandbox isolation from WSL.

## 2. Shared stack test boundary

Full contract/security/e2e tests that require Docker run on Manas's primary Ubuntu VM. Ask Manas for a test window,
connect over SSH as `bhavya`, and run only the requested test targets. Do not run `make up`, `make down` or
`make demo-reset`; Manas operates the one active stack. Send the exact command, exit code and output location back
to him and record your own handoff.

Never run stack resets while another person is collecting evidence. If the primary host becomes unavailable, only
Manas can authorize a handoff to Parth's prepared cold backup VM.

## 3. Browser and UI development

The original AI target is pending a four-person change request under `docs/16_BUILD_NOW_HOST_LATER.md`; the RTX 3050
is not needed for the current local work. For local console development,
coordinate with Manas on the approved proxy/dev-server URL. Session cookies use `Secure` and `SameSite=Strict`,
so test login over the configured HTTPS path rather than weakening cookie flags to accommodate local HTTP.

## 4. Work ownership

Edit only `web/`, `tools/verify_audit.py`, `tests/contract/`, `tests/security/`, `tests/e2e/`, `evidence/`, and
`team/bhavya/work/`. Do not edit another owner's code, build wiring, or frozen contracts. Submit PRs from
`work/bhavya` to `integration`; Manas alone merges them.

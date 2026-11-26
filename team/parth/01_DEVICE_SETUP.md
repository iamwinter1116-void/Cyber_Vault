# Parth · runtime development and cold backup host

Known hardware: i7 HX class CPU, RTX 5050 with 8 GB VRAM, 24 GB RAM. The laptop brand/OS and exact logical CPU
count must be verified locally. Manas owns the primary demo host; Parth owns runtime code and can prepare a cold
backup VM if there is enough time.

## 1. Development machine

Keep the code checkout on a Linux filesystem when using Linux tools. Use WSL 2 or a native Linux environment for
editing, lint and unit tests. Do not use WSL or Docker Desktop to claim gVisor, network, cgroup or storage security.
The actual container runtime and isolation checks run on Manas's Ubuntu Server 24.04 primary VM over SSH.

## 2. Primary VM access

Manas provisions the primary Ubuntu VM with the documented initial size of 6 vCPU, 12 GB RAM and 80 GB disk.
Coordinate SSH access and the test window with him before running B0 or any Docker/runtime task. Confirm host identity
with `hostname`, `uname -a`, `/proc/version`, `docker info`, and `runsc --version` before recording evidence.
Use the official Docker Engine and gVisor instructions; default gVisor platform is `systrap`.

Parth owns the code in `host/`, `services/runner/`, and `sandbox/`. Manas owns the VM, Compose, secrets, stack lifecycle
and resets. Do not run `make up`, `make down`, or `make demo-reset` on the primary host.

## 3. Optional cold backup VM

Only if the team has time, prepare an Ubuntu 24.04 VM as a cold backup using the same hypervisor family as Manas.
Start from 4 vCPU / 8 GB RAM / 80 GB disk; record actual limits. Do not start its stack while Manas's primary stack
is active. A backup exercise requires Manas to announce the handoff, stop primary services, confirm which host is active,
and authorize Parth to start the backup. After the drill, stop it and return control explicitly to Manas.

Do not let two runner/reaper processes operate on the same Docker daemon or two demo stacks advertise the same URL.
The recovery handoff records the active database state, witness state, demo URL, last passing commit, and commands run.

## 4. Hardware and workloads

The RTX 5050 is not used by the mandatory objectives. Do not pass the GPU or any host device into the sandbox.
The original AI target is pending a four-person change request under `docs/16_BUILD_NOW_HOST_LATER.md`.
Do not implement a model stub or add GPU access without that decision and an explicitly tested network policy.

## 5. Evidence and ownership

Preflight and security evidence must identify whether it came from Manas's primary VM or a formally handed-off backup.
Never label WSL output as a runtime pass. PRs go from `work/parth` to `integration`; Manas alone merges. Keep work
limited to your owned paths and append handoffs only to `team/parth/work/`.

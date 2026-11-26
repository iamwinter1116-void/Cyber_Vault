# Manas · primary host and maintainer workstation

Known hardware: Ryzen 9 9955HX, RTX 5070 Ti with 12 GB VRAM, 32 GB RAM. Verify the exact laptop OS, logical CPU count,
virtualization status, available disk, and GPU model before setup; the hardware label alone is not host evidence.

## Primary demo VM

Use Ubuntu Server 24.04 LTS in a full VM. The project contract and risk plan expect a real Linux host for Docker Engine
and gVisor; WSL and Docker Desktop are not acceptable evidence for sandbox security.

| Setting | Initial value | Why |
| --- | --- | --- |
| Guest OS | Ubuntu Server 24.04 LTS | Matches the project compatibility plan |
| vCPU | 6 | Preserves the admission-control/demo baseline |
| RAM | 12 GB | Matches current host-capacity assumptions; leaves memory for Windows and the hypervisor |
| Disk | 80 GB dynamically allocated | Holds images, evidence and bounded volumes |
| Network | Host can reach VM; sandbox networks cannot reach host/control plane/internet | Enables team/jury access without weakening tenant isolation |
| Runtime | Docker Engine + gVisor `runsc`, default `systrap` | `runsc` must be real and inspectable |

Do not enable GPU passthrough for tenants. The mandatory AI workload is an offline stub. A real GPU-backed model is a
post-G4 stretch only and must be treated as a network/isolation change, not a harmless performance toggle.

## Host checks and safe operation

1. Record `hostname`, OS release, CPU count, RAM, free disk and virtualization status in `evidence/preflight.md`.
2. Install Docker Engine and `runsc` from their official instructions; record versions and exact commands.
3. Run the documented preflight and spikes inside the VM. Never infer gVisor isolation from a local Windows or WSL run.
4. Bind public access only through the TLS proxy. Do not publish PostgreSQL, the API, runner, or notary ports.
5. Keep credentials and the 32-byte notary seed in ignored secret files with restrictive permissions.
6. Take snapshots before host/runtime changes and name the clean/preflight-passing snapshots clearly.
7. Only Manas operates `make up`, `make down`, `make demo-reset`, runner restarts and the primary daemon.
8. Announce a reset or shutdown to all contributors first; capture evidence and coordinate test windows.

## Local maintainer tools

Use Windows for hypervisor management and SSH; use the VM for all stack/runtime checks. Keep the source checkout in the
VM or a Linux filesystem if using Linux tools. WSL can be used for editing and docs, but a WSL `runsc` result never counts.
Do not install an unapproved dependency or expose a host mount/socket to a sandbox to simplify setup.

## Backup and recovery

Parth may prepare a smaller Ubuntu VM on his 24 GB laptop as a cold backup. It must not run concurrently with the primary
Docker stack. A host handoff names who stops the current daemon, who starts the backup, the active URL, and the database
snapshot/witness state. Henil and Bhavya do not operate Docker stacks. Record the exact backup test in the handoff log.

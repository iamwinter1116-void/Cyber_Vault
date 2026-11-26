# Hand-off notes · Parth (role B)

The agent appends one note at the end of every session (prompt P-HANDOFF), in the format of
`docs/07_ANTI_HALLUCINATION.md` section 5. Newest at the bottom. Teammates read this file to learn what is
really finished: only what was run and seen belongs here.


## 2026-11-26 · B0 host preflight and spikes (scripts written; not yet run on the demo VM)
```
TASK: B0 · Host preflight and spikes (gate G0)
STATUS: partial -- scripts written and locally checked; "done when" needs Manas's primary Ubuntu VM
CHANGED: host/preflight.sh (new, 118 lines), host/setup_host.sh (new, 32 lines); total 150 = B0 limit
COMMANDS RUN (with exit codes), on Parth's Windows laptop (MINGW64_NT-10.0-26300, Git Bash), NOT the demo VM:
  $ git switch work/parth                      -> 0  (base 6dc40c8, tree was clean)
  $ sh -n / dash -n host/preflight.sh, host/setup_host.sh   -> 0 (all four)
  $ wc -l host/*.sh                            -> 118 + 32 = 150
  $ grep -nE 'privileged|cap_add|docker\.sock|network host|TODO|FIXME' host/*.sh -> 1 (no hits)
  $ sh host/preflight.sh (scratch copy)        -> 1
    FAIL 1 os: MINGW64_NT-10.0-26300/x86_64    (stops at check 1 as required; no later check ran)
    header also recorded: cpus=24 mem_kb=24786004 for this laptop
  $ check-1 case logic fed 4 /proc/version samples -> WSL2 FAIL, WSL1 FAIL, Ubuntu x86_64 PASS, aarch64 FAIL
  $ wsl.exe -d Ubuntu -- sh host/preflight.sh  -> could not start: Wsl/Service/CreateInstance/CreateVm/HCS/HCS_E_SERVICE_NOT_AVAILABLE
  $ sh host/setup_host.sh (non-root)           -> 1  "setup_host.sh: run as root (sudo)"
TESTS: none of T-ISO/T-RES run (not applicable before B1); preflight checks 2-10 and all three spikes NOT run
VERIFIED FACTS:
  Docker Engine apt install steps -- https://docs.docker.com/engine/install/ubuntu/ (read 2026-11-26 via a fetch tool; supports 24.04 and 26.04 LTS)
  gVisor apt install steps; apt package auto-configures an installed Docker; tarball path uses `runsc install` + `systemctl reload docker`
    -- https://gvisor.dev/docs/user_guide/install/ (read 2026-11-26)
  gateway_mode_ipv4=isolated is allowed only with --internal and assigns no bridge address
    -- https://docs.docker.com/engine/network/port-publishing/ (read 2026-11-26; page states no minimum Engine version)
UNVERIFIED / ASSUMED:
  - Fetched commands were extracted by a summarizing fetch tool; re-read both install pages on the VM before running setup_host.sh.
  - setup_host.sh: added -y; Docker's sources file written with printf instead of the page's `tee <<EOF` (same fields).
  - docker info --format field names (OperatingSystem, ServerVersion, CgroupVersion, CgroupDriver, Driver, DriverStatus,
    DockerRootDir, Runtimes) not checked against the installed Engine; a wrong name makes check 2 FAIL visibly.
  - busybox applets used by the spikes (nc -w, httpd -f -p, dd, tail, head -c) not checked on the pulled image;
    the network spike pairs every refusal with a positive control (peer reached, host listener up) so a broken nc FAILs, not PASSes.
  - Container cgroup directory located by `find /sys/fs/cgroup -name *<id>*`; path layout under runsc not yet observed.
  - Storage V1 relies on the local volume driver accepting o=loop; that is exactly what the spike measures.
  - Interpretations of mine, not stated in the docs: FAIL in checks 6-10 makes the final exit non-zero; "8 GB" = 7,812,500 kB MemTotal;
    "20 GB free" = 19,531,250 kB on DockerRootDir; spike image default busybox; public address default 1.1.1.1;
    CPU spike pass bound 57.5 % (115 % of --cpus 0.5, borrowed from T-RES-04); host listener on port 18080 via python3.
  - With zero sandbox/templates/*/template.yaml (none exist yet) check 10 passes and says "0 template.yaml files".
DEGRADED PATHS: none taken. If gateway_mode_ipv4=isolated is rejected, check 6 FAILs and the firewall fallback
  is NOT applied automatically (needs a team decision, docs/08 section 1 item 6).
NEW DEPENDENCIES: none installed. Host tools used at run time: docker, runsc, python3, mkfs.ext4, truncate, timedatectl, systemd-detect-virt.
OPEN RISKS / QUESTIONS FOR HUMANS:
  - Manas: please add Makefile target `preflight:` running `sh host/preflight.sh` (repo root), plus SSH access and a test
    window on the primary VM. Run `sudo sh host/setup_host.sh` once, then `sh host/preflight.sh` as a docker-group user.
  - Bhavya/Manas: preflight writes evidence/preflight.md (Bhavya's path); agree who commits it after the VM run.
  - CLAUDE.local.md is git-ignored at every depth (.gitignore:1), so team/parth/CLAUDE.local.md is absent from my clone.
  - Directory modes/owners for /var/lib/abhedya/{vol,quarantine,witness} are not specified; setup creates them root-owned default mode.
  - Snapshot the VM after B0 passes (team/parth/00_START_HERE.md item 5).
NEXT: run B0 on the primary VM and paste evidence/preflight.md here; then B1.
```

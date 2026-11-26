#!/bin/sh
# B0 host preflight: the ten checks of docs/08 section 1, in order. Ubuntu demo VM only, from the repository root.
# Checks 1-5 stop at the first FAIL; a FAIL in 6-10 is reported and makes the final exit non-zero.
set -eu
OUT=evidence/preflight.md
IMG=${PREFLIGHT_IMAGE:-busybox}
PUB=${PREFLIGHT_PUBLIC_ADDR:-1.1.1.1}
TAG=abh-preflight-$$; FAILED=0; LPID=
TMP=$(mktemp -d)
mkdir -p "$(dirname "$OUT")"; : >"$OUT"
log() { printf '%s\n' "$*" | tee -a "$OUT"; }
cleanup() {
  [ -z "$LPID" ] || kill "$LPID" 2>/dev/null || true
  if command -v docker >/dev/null 2>&1; then
    docker ps -aq --filter label=abh.preflight=true 2>/dev/null | xargs -r docker rm -f >/dev/null 2>&1 || true
    docker network ls -q --filter label=abh.preflight=true 2>/dev/null | xargs -r docker network rm >/dev/null 2>&1 || true
    docker volume ls -q --filter label=abh.preflight=true 2>/dev/null | xargs -r docker volume rm >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT
# res PASS|FAIL <check> <name> <observed value>; run <cmd...> records the command, output and exit code
res() { log "$1 $2 $3: $4"; [ "$1" = PASS ] && return 0; FAILED=1; [ "$2" -gt 5 ] || exit 1; }
run() { rc=0; "$@" >"$TMP/o" 2>&1 || rc=$?
  { printf '\n```\n$ %s\n' "$*"; cat "$TMP/o"; printf 'exit=%s\n```\n' "$rc"; } >>"$OUT"; return "$rc"; }
sbx() { docker run --runtime=runsc --label abh.preflight=true "$@"; }
log "# Host preflight $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "host=$(hostname) kernel=$(uname -r) hypervisor=$(systemd-detect-virt 2>/dev/null || true)"
log "cpus=$(nproc 2>/dev/null || echo ?) mem_kb=$(awk '/^MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo ?)"
V=$(cat /proc/version 2>/dev/null || echo none)
case "$(uname -s)/$(uname -m)/$V" in
  */*/*[Mm]icrosoft*) res FAIL 1 os "WSL detected: $V" ;;
  Linux/x86_64/*) res PASS 1 os "Linux x86_64, /proc/version has no Microsoft" ;;
  *) res FAIL 1 os "$(uname -s)/$(uname -m)" ;;
esac
F='OS={{.OperatingSystem}} Server={{.ServerVersion}} Cgroup={{.CgroupVersion}} Driver={{.CgroupDriver}} Storage={{.Driver}} Status={{.DriverStatus}} Root={{.DockerRootDir}} Runtimes={{range $k, $v := .Runtimes}}{{$k}} {{end}}'
INFO=$(docker info --format "$F" 2>&1) || res FAIL 2 docker "docker info failed: $INFO"
case "$INFO" in *"Docker Desktop"*) res FAIL 2 docker "Docker Desktop: $INFO" ;; *) res PASS 2 docker "$INFO" ;; esac
RV=$(runsc --version 2>&1 | head -1) || res FAIL 3 runsc "runsc --version failed: $RV"
case "$INFO" in *"Runtimes="*runsc*) res PASS 3 runsc "$RV; registered" ;; *) res FAIL 3 runsc "not under Runtimes" ;; esac
run docker run --rm --runtime=runsc hello-world && res PASS 4 hello-world "exit 0" || res FAIL 4 hello-world "see output"
docker image inspect "$IMG" >/dev/null 2>&1 || run docker pull "$IMG" || res FAIL 5 kernel "cannot get $IMG"
log "spike image $IMG = $(docker image inspect --format '{{.Id}} {{.RepoDigests}}' "$IMG")"
GK=$(sbx --rm "$IMG" uname -r 2>&1) || res FAIL 5 kernel "runsc uname failed: $GK"
[ "$GK" != "$(uname -r)" ] && res PASS 5 kernel "sandbox=$GK host=$(uname -r)" || res FAIL 5 kernel "same as host: $GK"
# 6 SPIKE network. Each refusal is paired with a positive control, so a broken probe cannot pass as isolation.
NET=$TAG-net
probe() { sbx --rm --network "$NET" "$IMG" nc -w 3 "$1" "$2" </dev/null >/dev/null 2>&1; }
if run docker network create --internal -o com.docker.network.bridge.gateway_mode_ipv4=isolated --label abh.preflight=true "$NET"; then
  GW=$(docker network inspect --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' "$NET")
  HIP=$(hostname -I | cut -d' ' -f1)
  python3 -m http.server 18080 --bind 0.0.0.0 >/dev/null 2>&1 & LPID=$!
  sleep 2
  run sbx -d --name "$TAG-srv" --network "$NET" "$IMG" httpd -f -p 8080 || true
  hostctl() { python3 -c "import socket,sys; socket.create_connection((sys.argv[1], int(sys.argv[2])), 3)" "$1" "$2" 2>/dev/null; }
  hostctl "$HIP" 18080 && HL=up || HL=down
  hostctl "$PUB" 443 && HN=yes || HN=no
  probe "$TAG-srv" 8080 && PEER=reached || PEER=unreached
  LEAK=
  for t in "$HIP:18080" "$PUB:53" "$PUB:443" ${GW:+"$GW:18080"}; do
    if probe "${t%:*}" "${t#*:}"; then LEAK="$LEAK $t"; fi
  done
  M="mode=isolated gateway='${GW}' peer=$PEER host_listener($HIP:18080)=$HL host_internet=$HN leaks='${LEAK# }'"
  [ "$PEER" = reached ] && [ "$HL" = up ] && [ -z "$LEAK" ] && res PASS 6 network "$M" || res FAIL 6 network "$M"
else
  res FAIL 6 network "gateway_mode_ipv4=isolated rejected; --internal plus host firewall fallback needs a decision, not applied"
fi
# 7 SPIKE limits under runsc.
CG() { find /sys/fs/cgroup -maxdepth 4 -type d -name "*$(docker inspect --format '{{.Id}}' "$1")*" 2>/dev/null | head -1; }
run sbx --name "$TAG-mem" -m 64m --memory-swap 64m "$IMG" sh -c 'head -c 209715200 /dev/zero | tail' || true
MS=$(docker inspect --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "$TAG-mem" 2>&1) || MS="inspect failed: $MS"
case "$MS" in *exit=137*|*oom=true*) res PASS 7a memory "64m container allocating 200 MB killed: $MS" ;; *) res FAIL 7a memory "not killed: $MS" ;; esac
if run sbx -d --name "$TAG-fork" --pids-limit 64 -m 128m "$IMG" sh -c 'b() { b | b & }; b; sleep 60'; then
  sleep 10; t0=$(date +%s%N); sh -c true; HMS=$(( ($(date +%s%N) - t0) / 1000000 ))
  D=$(CG "$TAG-fork" 2>/dev/null || true)
  run docker stats --no-stream --format '{{.PIDs}} pids {{.CPUPerc}} cpu {{.MemUsage}}' "$TAG-fork" || true
  run sh -c "cd '$D' && grep -H . pids.max pids.current pids.events memory.events" || true
  CONT=$(cat "$D/pids.events" "$D/memory.events" 2>/dev/null | awk '$2>0 && ($1=="max"||$1=="oom"||$1=="oom_kill"){printf "%s=%s ",$1,$2}')
  [ "$HMS" -lt 1000 ] && res PASS 7b forkbomb "host fork took ${HMS} ms; contained by: ${CONT:-no limit counter rose}" \
    || res FAIL 7b forkbomb "host fork took ${HMS} ms"
else res FAIL 7b forkbomb "container with --pids-limit 64 did not start under runsc (risk R-03)"; fi
run sbx -d --name "$TAG-cpu" --cpus 0.5 "$IMG" sh -c 'while :; do :; done' || true
D=$(CG "$TAG-cpu" 2>/dev/null || true); sleep 2
if [ -n "$D" ] && [ -f "$D/cpu.stat" ]; then
  u0=$(awk '/^usage_usec/{print $2}' "$D/cpu.stat"); t0=$(date +%s%N); sleep 10
  u1=$(awk '/^usage_usec/{print $2}' "$D/cpu.stat"); el=$(( ($(date +%s%N) - t0) / 1000 ))
  P10=$(( (u1 - u0) * 1000 / el ))
  M="--cpus 0.5 busy loop used $((P10 / 10)).$((P10 % 10)) % of one CPU over 10 s (cgroup cpu.stat)"
  [ "$P10" -le 575 ] && res PASS 7c cpu "$M; bound 57.5 % = 115 % of limit (T-RES-04)" || res FAIL 7c cpu "$M"
else res FAIL 7c cpu "cgroup directory with cpu.stat not found for $TAG-cpu"; fi
# 8 SPIKE storage ladder of docs/08 section 4, 16 MiB quota; keep the first method that passes.
fill() { # writes until full as UID 1000; pass = "No space" at or below 16 MiB
  run sbx --rm --user 1000:1000 "$@" "$IMG" sh -c 'dd if=/dev/zero of=/workspace/f bs=1048576 count=64; ls -l /workspace/f' || true
  sz=$(awk '/\/workspace\/f$/{print $5}' "$TMP/o"); grep -q 'No space' "$TMP/o" && [ "${sz:-99999999}" -le 16777216 ]
}
SD=$(mktemp -d /var/tmp/abh-preflight.XXXXXX); A0=$(df -Pk "$SD" | awk 'NR==2{print $4}')
truncate -s 16M "$SD/img" && mkfs.ext4 -q -E root_owner=1000:1000 "$SD/img" \
  && run docker volume create -d local -o type=ext4 -o device="$SD/img" -o o=loop --label abh.preflight=true "$TAG-v1" \
  && fill --mount "type=volume,src=$TAG-v1,dst=/workspace" && S=V1
A1=$(df -Pk "$SD" | awk 'NR==2{print $4}')
if [ -z "${S:-}" ] && run docker volume create -d local -o type=tmpfs -o device=tmpfs -o o=size=16m,uid=1000,gid=1000 \
  --label abh.preflight=true "$TAG-v2" && fill --mount "type=volume,src=$TAG-v2,dst=/workspace"; then S=V2; fi
if [ -z "${S:-}" ] && fill --tmpfs /workspace:size=16m,uid=1000,gid=1000; then S=V3; fi
docker volume rm "$TAG-v1" >/dev/null 2>&1 || true; rm -rf "$SD"
[ -n "${S:-}" ] && res PASS 8 storage "method=$S; host free space drop during V1=$((A0 - A1)) kB (quota 16384)" || res FAIL 8 storage "V1, V2, V3 all failed"
NTP=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo unknown)
CPUS=$(nproc); MEM=$(awk '/^MemTotal/{print $2}' /proc/meminfo)
ROOT=$(docker info --format '{{.DockerRootDir}}'); FREE=$(df -Pk "$ROOT" | awk 'NR==2{print $4}')
M="ntp_synchronized=$NTP cpus=$CPUS mem_kb=$MEM free_kb($ROOT)=$FREE"
[ "$NTP" = yes ] && [ "$CPUS" -ge 4 ] && [ "$MEM" -ge 7812500 ] && [ "$FREE" -ge 19531250 ] && res PASS 9 capacity "$M" || res FAIL 9 capacity "$M"
N=0; MISS=
for f in sandbox/templates/*/template.yaml; do
  [ -f "$f" ] || continue; N=$((N + 1))
  for d in $(grep -o 'sha256:[0-9a-f]\{64\}' "$f" || true); do docker image inspect "$d" >/dev/null 2>&1 || MISS="$MISS $d"; done
done
[ -z "$MISS" ] && res PASS 10 images "$N template.yaml files; every digest present locally" || res FAIL 10 images "missing:$MISS"
log "RESULT: $([ "$FAILED" = 0 ] && echo PASS || echo FAIL)"
exit "$FAILED"

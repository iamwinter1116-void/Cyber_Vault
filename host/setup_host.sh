#!/bin/sh
# Idempotent host setup (docs/08 section 1): Docker Engine, gVisor runsc, /var/lib/abhedya dirs, NTP client.
# Install commands follow https://docs.docker.com/engine/install/ubuntu/ and
# https://gvisor.dev/docs/user_guide/install/ (apt sections, read 2026-11-26), run as root, with -y added.
set -eu
[ "$(id -u)" = 0 ] || { echo "setup_host.sh: run as root (sudo)"; exit 1; }
if grep -qi microsoft /proc/version; then echo "setup_host.sh: WSL is not a supported host"; exit 1; fi
. /etc/os-release; [ "$ID" = ubuntu ] || { echo "setup_host.sh: Ubuntu only, found $ID"; exit 1; }
if ! command -v dockerd >/dev/null 2>&1; then
  OLD=$(dpkg --get-selections docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc 2>/dev/null | cut -f1)
  [ -z "$OLD" ] || apt remove -y $OLD
  apt update && apt install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf 'Types: deb\nURIs: https://download.docker.com/linux/ubuntu\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' \
    "${UBUNTU_CODENAME:-$VERSION_CODENAME}" "$(dpkg --print-architecture)" >/etc/apt/sources.list.d/docker.sources
  apt update
  apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
if ! command -v runsc >/dev/null 2>&1; then
  apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg
  curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor --yes -o /usr/share/keyrings/gvisor-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
    >/etc/apt/sources.list.d/gvisor.list
  apt-get update && apt-get install -y runsc
fi
# The gVisor apt package configures an installed Docker itself; register explicitly only if it did not.
docker info --format '{{range $k, $v := .Runtimes}}{{$k}} {{end}}' | grep -qw runsc || { runsc install; systemctl reload docker; }
mkdir -p /var/lib/abhedya/vol /var/lib/abhedya/quarantine /var/lib/abhedya/witness
timedatectl set-ntp true
echo "setup_host.sh: done; now run: sh host/preflight.sh"

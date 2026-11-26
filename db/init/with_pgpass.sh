#!/bin/sh
# Copy a mounted libpq password file to a private temporary file before exec.
# Required for bind-mounted Compose secrets whose host-side mode cannot be
# represented as 0600 inside Linux (notably Docker Desktop on Windows).
set -eu

if [ "$#" -lt 2 ]; then
  printf 'usage: with_pgpass.sh SECRET_FILE COMMAND [ARG... ]\n' >&2
  exit 64
fi

secret_file=$1
shift
if [ ! -f "$secret_file" ] || [ ! -r "$secret_file" ]; then
  printf 'libpq password file is missing or unreadable\n' >&2
  exit 1
fi

tmp_dir=${TMPDIR:-/tmp}
if [ ! -d "$tmp_dir" ] || [ ! -w "$tmp_dir" ]; then
  printf 'temporary directory is missing or not writable\n' >&2
  exit 1
fi

umask 077
pgpass_file=$(mktemp "$tmp_dir/abh-pgpass.XXXXXX") || {
  printf 'could not create private libpq password file\n' >&2
  exit 1
}
trap 'rm -f "$pgpass_file"' EXIT HUP INT TERM
if ! cat "$secret_file" >"$pgpass_file"; then
  printf 'could not copy libpq password file\n' >&2
  exit 1
fi
chmod 600 "$pgpass_file"
export PGPASSFILE=$pgpass_file
exec "$@"

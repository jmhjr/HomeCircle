#!/usr/bin/env bash
# One newly owned native Linux guest; no connection to any existing HA instance.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in python3 qemu-system-x86_64 qemu-img timeout; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ -r /dev/kvm && -w /dev/kvm ]] || { echo accessible_kvm_required >&2; exit 2; }
[[ -n ${GITHUB_TOKEN:-} ]] || { echo ephemeral_job_token_required >&2; exit 2; }
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# Existing work/cleanup ceilings are unchanged from the executed donor.
exec timeout --signal=TERM --kill-after=45s 5700s python3 -I -B "$script_dir/controller.py" "$@"


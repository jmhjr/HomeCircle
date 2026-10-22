#!/usr/bin/env bash
# Own only the fresh native Linux guest created by this controller.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in python3 qemu-system-x86_64 qemu-img timeout; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ -r /dev/kvm && -w /dev/kvm ]] || { echo accessible_kvm_required >&2; exit 2; }
unset GITHUB_TOKEN GH_TOKEN
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec timeout --signal=TERM --kill-after=45s 5700s python3 -B "$script_dir/controller.py" "$@"

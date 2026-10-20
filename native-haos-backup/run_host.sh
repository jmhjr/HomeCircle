#!/usr/bin/env bash
# Only this fresh native Linux guest is owned by this launcher.
set -Eeuo pipefail
umask 077
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]] || { echo native_linux_amd64_required >&2; exit 2; }
for executable in python3 qemu-system-x86_64 qemu-img timeout; do
  command -v "$executable" >/dev/null || { echo required_host_command_missing >&2; exit 2; }
done
[[ -r /dev/kvm && -w /dev/kvm ]] || { echo accessible_kvm_required >&2; exit 2; }
unset GITHUB_TOKEN GH_TOKEN
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
# The controller keeps its own monotonic deadline and reserved cleanup time.
# GNU timeout additionally bounds a stalled interpreter or host operation.
exec timeout --signal=TERM --kill-after=45s 5700s python3 -B "$script_dir/controller.py" "$@"

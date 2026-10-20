"""Read-only GitHub/KVM capability receipt; execute only on disposable Linux."""
import sys

if sys.platform != "linux":
    raise SystemExit("linux_required")

import fcntl
import json
import os
from pathlib import Path
import platform
import urllib.request


def main():
    receipt = {"schema": 1, "outcome": "failed", "native_amd64": False,
               "kvm_api": None, "kvm_vm_created": False, "authenticated_reads": [],
               "owner_token_used": False, "virtual_machine_booted": False}
    output = Path("preflight-results")
    output.mkdir(mode=0o700)
    try:
        if platform.machine() != "x86_64":
            raise RuntimeError("native_amd64_required")
        receipt["native_amd64"] = True
        kvm = os.open("/dev/kvm", os.O_RDWR | os.O_CLOEXEC)
        try:
            receipt["kvm_api"] = fcntl.ioctl(kvm, 0xAE00, 0)
            if receipt["kvm_api"] != 12:
                raise RuntimeError("kvm_api_refused")
            vm = fcntl.ioctl(kvm, 0xAE01, 0)
            os.close(vm)
            receipt["kvm_vm_created"] = True
        finally:
            os.close(kvm)
        token = os.environ["GH_TOKEN"]
        if not token or "\n" in token:
            raise RuntimeError("job_token_required")
        endpoints = [
            ("own_repository", "repos/jmhjr/HomeCircle"),
            ("validation_branch", "repos/jmhjr/HomeCircle/branches/codex%2Fnative-amd64-validation"),
            ("public_hacs_repository", "repos/hacs/integration"),
            ("public_hacs_contents", "repos/hacs/integration/contents/custom_components/hacs/manifest.json?ref=2.0.5"),
            ("public_hacs_release", "repos/hacs/integration/releases/tags/2.0.5"),
            ("rate_limit", "rate_limit"),
        ]
        for label, endpoint in endpoints:
            request = urllib.request.Request("https://api.github.com/" + endpoint,
                headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                         "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "HomeCircle-isolated-preflight"})
            with urllib.request.urlopen(request, timeout=20) as response:
                body = response.read(2 * 1024**2 + 1)
                if response.status != 200 or len(body) > 2 * 1024**2:
                    raise RuntimeError("github_read_refused")
                value = json.loads(body)
                if label == "rate_limit":
                    core = value["resources"]["core"]
                    receipt["rate_limit"] = {key: core[key] for key in ("limit", "remaining", "reset")}
                receipt["authenticated_reads"].append(label)
        receipt["outcome"] = "passed"
    except Exception as error:
        # Never print exception text, request headers, token or response body.
        receipt["failure_type"] = type(error).__name__
    temporary = output / "preflight.json.tmp"
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    temporary.replace(output / "preflight.json")
    print(json.dumps(receipt))
    return 0 if receipt["outcome"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

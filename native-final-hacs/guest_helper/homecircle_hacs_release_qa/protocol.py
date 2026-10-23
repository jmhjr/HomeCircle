"""Frozen public identity and finite phase definitions; no runtime imports."""
import hashlib
import json
import re

SOURCE = "b906d3ee51711d3455a497cc265fd3bc18f3adec"
CANDIDATE = "4f94a18e2f7862e9bd7f4c85250e5f10e4b8e1292ea9d7b263b441d2e1b77dd9"
INVENTORY = "e4bc34e3921e75157402cf643f87ed658d95c76505a448abb393fd90a304db12"
BASELINE = "fc0b365d9688459504f874af5c38393e24145d657f15f1def8ada9184f363285"
BASE_INVENTORY = "5e724f69ff20a711dd87b2a39ed96818781813bb6f1e7b3addedc6e048593d77"
VERSION = "1.0.0-rc.1"
TAG = "v" + VERSION
BASE_VERSION = "0.1.0-beta.20"
BASE_TAG = "v" + BASE_VERSION
REPOSITORY = "jmhjr/HomeCircle"
CORE = "2026.10.2"
HACS = "2.0.5"
HACS_SHA = "97be6b824a4f38e683728cc6dd72367f6b8bad0a43428b1b3b987a3087adf413"
PHASES = ("bootstrap_hacs", "fresh_download", "fresh", "fresh_remove", "fresh_removed",
          "baseline_download", "baseline", "upgrade_download", "upgraded", "restart",
          "rollback_download", "rollback", "reupgrade_download", "final")
DOWNLOADS = {"fresh_download": TAG, "baseline_download": BASE_TAG,
             "upgrade_download": TAG, "rollback_download": BASE_TAG, "reupgrade_download": TAG}
DISK = {name: ("candidate" if name in {"fresh_download", "fresh", "upgrade_download", "upgraded", "restart", "reupgrade_download", "final"}
              else "baseline" if name in {"baseline_download", "baseline", "rollback_download", "rollback"} else None)
        for name in PHASES}
LOADED = {name: ("candidate" if name in {"fresh", "fresh_remove", "upgraded", "restart", "rollback_download", "final"}
                else "baseline" if name in {"baseline", "upgrade_download", "rollback", "reupgrade_download"} else None)
          for name in PHASES}
ACTIVE = frozenset({"fresh", "baseline", "upgrade_download", "upgraded", "restart", "rollback_download", "rollback", "reupgrade_download", "final"})
ANCHOR_KEYS = frozenset({"schema", "source_commit", "tag", "version", "candidate_sha256", "inventory_sha256",
                         "release_id", "asset_id", "asset_bytes", "inventory_asset_id", "inventory_bytes",
                         "draft", "prerelease"})
PHASE_KEYS = frozenset({"schema", "phase", "outcome", "source_commit", "candidate_sha256", "baseline_sha256",
    "anchor_sha256", "branch_commit", "nonce_sha256", "core_version", "process", "hacs", "disk", "loaded",
    "frontend", "snapshot_sha256", "persisted_store_checked", "download_tag", "release_proof", "removed",
    "guard", "activity", "removed_activity_store", "provider_requests_denied", "provider_accounts", "recovery_api_calls", "normal_requirements"})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(same(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected, strict=True))
    return actual == expected


def check(condition, code):
    if not condition:
        raise ValueError(code)


def anchor_at(path, expected_sha):
    check(path.is_file() and not path.is_symlink() and path.stat().st_size < 16384, "release_anchor_path")
    raw = path.read_bytes()
    check(isinstance(expected_sha, str) and re.fullmatch(r"[0-9a-f]{64}", expected_sha)
          and digest(raw) == expected_sha, "release_anchor_hash")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            check(key not in result, "release_anchor_duplicate_key")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    check(isinstance(value, dict) and set(value) == ANCHOR_KEYS, "release_anchor_schema")
    fixed = {"schema": 1, "source_commit": SOURCE, "tag": TAG, "version": VERSION,
             "candidate_sha256": CANDIDATE, "inventory_sha256": INVENTORY, "asset_bytes": 628136,
             "inventory_bytes": 16674, "draft": False, "prerelease": True}
    check(all(type(value.get(key)) is type(item) and value[key] == item for key, item in fixed.items()), "release_anchor_identity")
    check(all(type(value.get(key)) is int and value[key] > 0 for key in ("release_id", "asset_id", "inventory_asset_id")), "release_anchor_ids_pending")
    return value

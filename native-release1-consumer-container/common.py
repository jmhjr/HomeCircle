"""Bounded immutable inputs and receipts for the disposable consumer witness."""

import ast
import hashlib
import importlib.util
import json
import re

SOURCE = "9bf03eb45d2cf43274074534e9dfe2de841f4011"
ARCHIVE = "c4530d94be3b2996f8d6c8948db88a51868566047d68558eefde7967f270a861"
INVENTORY = "9bdfba997d5437d354673a98c8b78d3875d459499281bca3e20bc629369dcb6b"
SUPPORT = "e97e3f71fc9f7ceb9391f86e0178c59c3b88a2fafe5f397e25a9fb69fe568e59"
SOURCE_CONFIG = "bce0379d11d76c53954380c3893a2cf581d539519168492f4235ffee9ba3be0d"
CONTROL = ".homecircle-consumer-qa"
DOMAIN = "homecircle_consumer_qa"
VERSION = "0.1.0-beta.20"
SETUP_STAGES = frozenset(
    {
        "preparer_boundary",
        "startup_identity",
        "source_inputs",
        "source_extract",
        "package_inspection",
        "fixture_staging",
        "cache_layout",
        "cache_install",
        "cache_versions",
        "source_recheck",
        "setup_receipt",
    }
)


class Refused(RuntimeError):
    pass


def check(value, code):
    if not value:
        raise Refused(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, expected=None, limit=64 * 1024**2):
    check(
        path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
        "input_file_refused",
    )
    raw = path.read_bytes()
    check(expected is None or sha(raw) == expected, "input_hash_refused")
    return raw


def load(name, path, expected):
    read(path, expected)
    spec = importlib.util.spec_from_file_location(name, path)
    check(spec is not None and spec.loader is not None, "module_spec_refused")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pins(path, expected):
    def unique(items):
        result = {}
        for key, value in items:
            check(key not in result, "duplicate_pin_refused")
            result[key] = value
        return result

    value = json.loads(read(path, expected, 256 * 1024), object_pairs_hook=unique)
    keys = {
        "schema",
        "target",
        "core",
        "python",
        "architecture",
        "machine",
        "image_repository",
        "image_digest",
        "image_id",
        "image_manifest",
        "constraints_sha256",
        "dependency_versions",
        "startup_versions",
        "startup_sources",
        "startup_scripts",
        "native_s6",
        "controls",
        "capability_mask",
    }
    check(
        isinstance(value, dict)
        and set(value) == keys
        and type(value["schema"]) is int
        and value["schema"] == 1,
        "pin_schema_refused",
    )
    check(
        value["core"] in {"2026.9.4", "2026.10.2"} and value["python"] == "3.14.6",
        "runtime_pin_refused",
    )
    check(
        value["architecture"] in {"amd64", "arm64"}
        and value["machine"]
        == {"amd64": "x86_64", "arm64": "aarch64"}[value["architecture"]],
        "architecture_pin_refused",
    )
    check(
        value["target"]
        == ("current" if value["core"] == "2026.10.2" else "minimum")
        + "-"
        + value["architecture"],
        "target_pin_refused",
    )
    check(
        value["image_repository"] == "ghcr.io/home-assistant/home-assistant"
        and value["capability_mask"] == "00000000a80425fb",
        "consumer_boundary_refused",
    )
    for key in ("image_digest", "image_id", "image_manifest"):
        check(
            isinstance(value[key], str)
            and re.fullmatch(r"sha256:[0-9a-f]{64}", value[key]),
            "image_pin_refused",
        )
    for key, count in (
        ("dependency_versions", 24),
        ("startup_versions", 21),
        ("startup_sources", 5),
        ("startup_scripts", 3),
        ("native_s6", 3),
        ("controls", 6),
    ):
        check(
            isinstance(value[key], dict) and len(value[key]) == count,
            "pin_mapping_refused",
        )
    check(
        re.fullmatch(r"[0-9a-f]{64}", value["constraints_sha256"]) is not None,
        "constraint_pin_refused",
    )
    check(
        value["constraints_sha256"]
        == {
            "2026.10.2": "7baa9a8f39ddeb9c5bb60a1036f6d5e33f4b84267f151f53cc2b95ef031a21b5",
            "2026.9.4": "962c9ccaf398e0b92b10ac9f765ac0f17e22238adc4e768deebc051ee8b60651",
        }[value["core"]]
        and value["startup_versions"].get("pyotp")
        == ("2.10.0" if value["core"] == "2026.10.2" else "2.9.0"),
        "endpoint_requirement_pin_refused",
    )
    for key in ("startup_sources", "startup_scripts", "native_s6", "controls"):
        check(
            all(
                isinstance(name, str)
                and isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest)
                for name, digest in value[key].items()
            ),
            "content_pin_refused",
        )
    return value


def controls(folder, value):
    for name, expected in value["controls"].items():
        check(
            name
            in {
                "common.py",
                "cache_child.py",
                "driver.py",
                "guest.py",
                "process_probe.py",
                "run_host.sh",
            },
            "control_name_refused",
        )
        read(folder / name, expected)


def atomic(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    check(len(raw) <= 256 * 1024, "receipt_size_refused")
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        stream.write(raw)
    temporary.chmod(0o600)
    temporary.replace(path)


def installed(target, inventory):
    check(target.is_dir() and not target.is_symlink(), "package_root_refused")
    actual = {}
    for path in target.rglob("*"):
        check(not path.is_symlink(), "package_link_refused")
        if path.is_file() and "__pycache__" not in path.parts:
            raw = path.read_bytes()
            actual[path.relative_to(target).as_posix()] = {
                "bytes": len(raw),
                "sha256": sha(raw),
            }
    check(len(actual) == 113 and actual == inventory, "package_inventory_refused")


def base_receipt(value):
    return {
        "schema": 1,
        "target": value["target"],
        "core": value["core"],
        "python": value["python"],
        "architecture": value["architecture"],
        "source_commit": SOURCE,
        "package_sha256": ARCHIVE,
        "package_files": 113,
        "version": VERSION,
        "prepared_config_cache": True,
        "fresh_online_resolution_claimed": False,
        "owner_accounts_used": False,
        "native_apple_worker_executed": False,
        "managed_haos_service_claimed": False,
        "release_published": False,
    }


def safe_failure(error, folder, *, setup_stage=None):
    allowed = set()
    catalog = [
        (name, None)
        for name in ("common.py", "driver.py", "guest.py", "process_probe.py")
    ]
    # Only the preparer has this support file. Guest diagnostics remain local
    # to their four controls; support literals are trusted only at its exact pin.
    support = folder / "package_support.py"
    if support.exists() or support.is_symlink():
        catalog.append(("package_support.py", SUPPORT))
    for name, expected in catalog:
        for node in ast.walk(ast.parse(read(folder / name, expected))):
            if isinstance(node, ast.Call):
                call = (
                    node.func.id
                    if isinstance(node.func, ast.Name)
                    else node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else ""
                )
                index = (
                    1
                    if call == "check"
                    else 0
                    if call in {"Refused", "RuntimeError"}
                    else None
                )
                if (
                    index is not None
                    and len(node.args) > index
                    and isinstance(node.args[index], ast.Constant)
                    and isinstance(node.args[index].value, str)
                    and re.fullmatch(r"[a-z_]{1,100}", node.args[index].value)
                ):
                    allowed.add(node.args[index].value)
    result = {
        "schema": 1,
        "outcome": "failed",
        "failure_type": type(error).__name__
        if type(error).__name__
        in {"Refused", "TimeoutError", "AssertionError", "RuntimeError", "OSError"}
        else "OtherError",
    }
    if isinstance(error, (Refused, RuntimeError)) and str(error) in allowed:
        result["failure_code"] = str(error)
    if isinstance(setup_stage, str) and setup_stage in SETUP_STAGES:
        result["setup_stage"] = setup_stage
    return result

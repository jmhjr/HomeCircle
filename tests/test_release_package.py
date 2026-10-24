"""Release/privacy checks use disposable source fixtures, no npm or HA startup."""

import hashlib
import json
from pathlib import Path
import stat
import sys
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_release as build  # noqa: E402
import validate_release as validate  # noqa: E402

CANARY = b"EXCLUDED_PRIVATE_STATE_CANARY"


def fixture_source(tmp_path, *, runtime=False):
    source = tmp_path / "integration"
    source.mkdir(parents=True)
    required = build.REQUIRED_FILES | (
        build.REQUIRED_RUNTIME_FILES if runtime else set()
    )
    for name in required - {"LICENSE"}:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            b"# public fixture\n" if name.endswith(".py") else b"public fixture\n"
        )
    (source / "manifest.json").write_text(
        json.dumps(
            {
                "domain": "homecircle",
                "version": "1.0.0",
                "codeowners": ["@example"],
                "documentation": "https://example.invalid/docs",
                "issue_tracker": "https://example.invalid/issues",
            }
        )
    )
    (source / "frontend.py").write_text('VERSION = "1.0.0"\n')
    (source / "strings.json").write_text("{}")
    (source / "translations/en.json").write_text("{}")
    license_path = tmp_path / "LICENSE"
    license_path.write_text("public integration license\n")
    return source, license_path


def write_member(source, name, value):
    path = source / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def manual_archive(path, payload, *, metadata=None, duplicate=None, reverse=False):
    names = sorted(payload, reverse=reverse)
    if duplicate:
        names.append(duplicate)
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            info = zipfile.ZipInfo(name, build.TIMESTAMP)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            if metadata is not None and name == "__init__.py":
                metadata(info)
            archive.writestr(info, payload[name])
    return path


def test_recursive_runtime_and_vendor_provenance_are_packaged(tmp_path):
    source, license_path = fixture_source(tmp_path, runtime=True)
    write_member(source, "_findmy_runtime/auth/__init__.py", b"")
    write_member(source, "_findmy_runtime/auth/nested/session.py", b"READY = True\n")
    write_member(source, "_vendor_findmy/util/helper.py", b"READY = True\n")
    payload = build.collect_payload(source, license_path)
    assert "_findmy_runtime/auth/nested/session.py" in payload
    assert "_vendor_findmy/util/helper.py" in payload
    assert build.REQUIRED_RUNTIME_FILES <= payload.keys()
    for name in (
        "_vendor_findmy/LICENSE.md",
        "_vendor_findmy/README.md",
        "_vendor_findmy/cloudkit/proto/cloudkit.proto",
        "_vendor_findmy/keychain/roots/101.crt",
        "_findmy_runtime/emulator/LICENSE",
        "_findmy_runtime/PROVENANCE.md",
    ):
        assert name in payload
    archive, _ = build.write_archive(payload, tmp_path / "release")
    assert (
        validate.inspect_archive(archive, archive.with_name("inventory.json"))
        == payload
    )


def test_retired_local_macos_cli_is_excluded_and_complete_notices_remain(tmp_path):
    root = Path(__file__).resolve().parents[1]
    actual = root / "custom_components/homecircle"
    source, license_path = fixture_source(tmp_path)
    # Keep the inherited notices, while forbidding the unsupported local-Mac
    # decryptor and its sole command-line consumer even in contaminated inputs.
    for name in ("LICENSE.md", "README.md"):
        write_member(source, f"_vendor_findmy/{name}",
                     (actual / "_vendor_findmy" / name).read_bytes())
    retired = {"_vendor_findmy/plist.py", "_vendor_findmy/__main__.py"}
    for name in retired:
        assert not (actual / name).exists()
        write_member(source, name, CANARY)
    payload = build.collect_payload(source, license_path)
    assert not retired & payload.keys()
    archive, _ = build.write_archive(payload, tmp_path / "release")
    packaged = validate.inspect_archive(archive, archive.with_name("inventory.json"))
    origin = b"08a59cab551721afb9dc9f829ad31dae8d5bd400"
    assert not retired & packaged.keys()
    for index, name in enumerate(sorted(retired)):
        unsafe = dict(payload, **{name: CANARY})
        injected = manual_archive(tmp_path / f"retired-{index}.zip", unsafe)
        with pytest.raises(build.ReleaseError, match="unsafe member"):
            validate.inspect_archive(injected)
    notices = packaged["_vendor_findmy/LICENSE.md"]
    beginning = b"MIT License\n\nCopyright (c) 2025 Shane B.\n"
    assert notices.count(beginning) == 1
    # Exact 1,065-byte LICENSE.TXT from the pinned OpenTagViewer origin above.
    # Verify the complete copyright, permission, condition, and disclaimer text.
    offset = notices.index(beginning)
    assert hashlib.sha256(notices[offset:offset + 1065]).hexdigest() == (
        "e5d3404f06c194c08bfd18bfe4d42ece466f28098177b38c14aeb2bfe6b39597"
    )
    assert origin in packaged["_vendor_findmy/README.md"]


def test_labs_state_identity_and_binaries_never_enter_archive(tmp_path):
    source, license_path = fixture_source(tmp_path, runtime=True)
    excluded = [
        "machine.json",
        "session.vault",
        "identity.json",
        "lab.py.txt",
        "work/diagnostic.py",
        "other_package/unreviewed.py",
        "_findmy_runtime/state/keys.py",
        "_findmy_runtime/labs/diagnostic.py",
        "_findmy_runtime/tests/test_worker.py",
        "_findmy_runtime/.storage/item.py",
        "_findmy_runtime/PRIVATE/copy.py",
        "_findmy_runtime/test_secrets.py",
        "_findmy_runtime/machine.json",
        "_findmy_runtime/device_identity.bin",
        "_findmy_runtime/emulator/AppleADI",
        "_findmy_runtime/emulator/libadi.so",
        "_vendor_findmy/__pycache__/client.pyc",
        "_vendor_findmy/lab/probe.py",
    ]
    for name in excluded:
        write_member(source, name, CANARY)
    payload = build.collect_payload(source, license_path)
    assert not set(excluded) & payload.keys()
    assert all(CANARY not in content for content in payload.values())
    archive, _ = build.write_archive(payload, tmp_path / "release")
    assert all(
        CANARY not in content for content in validate.inspect_archive(archive).values()
    )


def test_archive_and_inventory_are_deterministic(tmp_path):
    source, license_path = fixture_source(tmp_path, runtime=True)
    payload = build.collect_payload(source, license_path)
    first, report = build.write_archive(payload, tmp_path / "one")
    second, again = build.write_archive(
        dict(reversed(tuple(payload.items()))), tmp_path / "two"
    )
    assert first.read_bytes() == second.read_bytes()
    assert report == again
    assert (
        first.with_name("inventory.json").read_bytes()
        == second.with_name("inventory.json").read_bytes()
    )
    assert report["archive_sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == sorted(payload)
        assert all(
            item.date_time == build.TIMESTAMP
            and item.create_system == 3
            and item.external_attr >> 16 == stat.S_IFREG | 0o644
            for item in archive.infolist()
        )


@pytest.mark.parametrize("missing", sorted(build.REQUIRED_RUNTIME_FILES))
def test_archive_cannot_omit_required_runtime_or_license_files(tmp_path, missing):
    source, license_path = fixture_source(tmp_path, runtime=True)
    payload = build.collect_payload(source, license_path)
    del payload[missing]
    path = manual_archive(tmp_path / "missing.zip", payload)
    with pytest.raises(build.ReleaseError, match="required runtime"):
        validate.inspect_archive(path)


def test_runtime_is_optional_until_referenced_but_import_closure_is_checked(tmp_path):
    source, license_path = fixture_source(tmp_path)
    payload = build.collect_payload(source, license_path)
    assert not any(name.startswith("_findmy_runtime/") for name in payload)
    payload["findmy_provider.py"] = b"from ._findmy_runtime.provider import Provider\n"
    with pytest.raises(build.ReleaseError, match="imported runtime module"):
        build.validate_payload(payload)
    source, license_path = fixture_source(tmp_path / "runtime", runtime=True)
    payload = build.collect_payload(source, license_path)
    payload["_findmy_runtime/provider.py"] = b"from .bootstrap import bootstrap\n"
    with pytest.raises(build.ReleaseError, match="imported runtime module"):
        build.validate_payload(payload)
    payload["_findmy_runtime/bootstrap.py"] = b"def bootstrap(): pass\n"
    build.validate_payload(payload)


@pytest.mark.parametrize(
    "name",
    [
        "../private.py",
        "/private.py",
        "_findmy_runtime/machine.json",
        "_findmy_runtime/state/private.py",
        "_findmy_runtime/libadi.dylib",
        "work/probe.py",
        "_findmy_runtime/../private.py",
        "_findmy_runtime\\private.py",
    ],
)
def test_validation_refuses_private_or_unsafe_archive_members(tmp_path, name):
    source, license_path = fixture_source(tmp_path)
    payload = build.collect_payload(source, license_path)
    payload[name] = CANARY
    path = manual_archive(tmp_path / "unsafe.zip", payload)
    with pytest.raises(build.ReleaseError, match="unsafe member"):
        validate.inspect_archive(path)


def test_archive_duplicate_member_is_refused_before_extraction(tmp_path):
    source, license_path = fixture_source(tmp_path)
    payload = build.collect_payload(source, license_path)
    with pytest.warns(UserWarning, match="Duplicate"):
        path = manual_archive(
            tmp_path / "duplicate.zip", payload, duplicate="manifest.json"
        )
    with pytest.raises(build.ReleaseError, match="unique and sorted"):
        validate.inspect_archive(path)


@pytest.mark.parametrize(
    "metadata",
    [
        lambda info: setattr(info, "external_attr", (stat.S_IFLNK | 0o777) << 16),
        lambda info: setattr(info, "date_time", (2025, 1, 1, 0, 0, 0)),
        lambda info: setattr(info, "comment", b"unexpected"),
    ],
)
def test_unsafe_archive_metadata_is_refused(tmp_path, metadata):
    source, license_path = fixture_source(tmp_path)
    payload = build.collect_payload(source, license_path)
    path = manual_archive(tmp_path / "metadata.zip", payload, metadata=metadata)
    with pytest.raises(build.ReleaseError, match="unsafe member"):
        validate.inspect_archive(path)


def test_payload_symlink_to_private_source_is_refused(tmp_path):
    source, license_path = fixture_source(tmp_path)
    private = tmp_path / "private.py"
    private.write_bytes(CANARY)
    (source / "unexpected.py").symlink_to(private)
    with pytest.raises(build.ReleaseError, match="symbolic links"):
        build.collect_payload(source, license_path)


def test_inventory_tampering_is_refused(tmp_path):
    source, license_path = fixture_source(tmp_path)
    archive, _ = build.write_archive(
        build.collect_payload(source, license_path), tmp_path / "release"
    )
    inventory = archive.with_name("inventory.json")
    report = json.loads(inventory.read_text())
    report["files"]["frontend.py"]["sha256"] = "0" * 64
    inventory.write_text(json.dumps(report))
    with pytest.raises(build.ReleaseError, match="inventory"):
        validate.inspect_archive(archive, inventory)

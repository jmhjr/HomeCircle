"""Platform evidence stays bound to the archive and actual installed constraints."""

import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_release as build  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "platform_validate_candidate_test", ROOT / "scripts/platform_validate_candidate.py"
)
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def test_wrong_candidate_hash_is_refused_before_imports_or_workers(
    tmp_path, monkeypatch
):
    archive = tmp_path / "candidate.zip"
    archive.write_bytes(b"untrusted fixture")
    monkeypatch.setattr(
        subject,
        "installed_requirements",
        lambda *_: pytest.fail("wrong candidate reached dependency inspection"),
    )
    with pytest.raises(ValueError, match="^platform_candidate_hash_refused$"):
        subject.run_validation(archive, expected_sha256="0" * 64)


def test_satisfied_manifest_still_reports_transitive_core_constraint_mismatch(
    tmp_path, monkeypatch
):
    constraints = tmp_path / "package_constraints.txt"
    constraints.write_text("setuptools==81.0.0\n")
    distributions = {
        "anisette": SimpleNamespace(
            version="1.2.4",
            metadata={"Name": "anisette"},
            requires=["fs>=2.4.16", "missing-cli; extra == 'cli'"],
        ),
        "fs": SimpleNamespace(
            version="2.4.16",
            metadata={"Name": "fs"},
            requires=["setuptools"],
        ),
        "setuptools": SimpleNamespace(
            version="84.0.0",
            metadata={"Name": "setuptools"},
            requires=[],
        ),
        "homeassistant": SimpleNamespace(
            version="2026.9.4",
            metadata={"Requires-Python": ">=3.14.2"},
            locate_file=lambda _: constraints,
        ),
    }
    monkeypatch.setattr(
        subject.importlib.metadata, "distribution", distributions.__getitem__
    )
    monkeypatch.setattr(
        subject.importlib,
        "import_module",
        lambda name: SimpleNamespace(__file__=str(tmp_path / "__init__.py"))
        if name == "homeassistant"
        else pytest.fail("unexpected import"),
    )
    result = subject.installed_requirements(["anisette==1.2.4"])
    assert result["core_constraint_mismatches"] == [
        {
            "package": "setuptools",
            "installed": "84.0.0",
            "constraint": "setuptools==81.0.0",
        }
    ]
    assert result["installed_dependency_closure"] == {
        "anisette": "1.2.4",
        "fs": "2.4.16",
        "setuptools": "84.0.0",
    }


@pytest.mark.parametrize("layout", ["site-packages", "src/homeassistant"])
def test_constraints_follow_active_core_origin_for_wheel_and_editable_layouts(
    tmp_path, monkeypatch, layout
):
    package = tmp_path / layout / "homeassistant"
    package.mkdir(parents=True)
    origin = package / "__init__.py"
    origin.write_text("# Synthetic Core package origin only.\n")
    raw = b"# Active Core constraints\nsetuptools==81.0.0\n"
    (package / "package_constraints.txt").write_bytes(raw)
    monkeypatch.setattr(
        subject.importlib,
        "import_module",
        lambda name: SimpleNamespace(__file__=str(origin))
        if name == "homeassistant"
        else pytest.fail("unexpected import"),
    )
    monkeypatch.setattr(
        subject.importlib.metadata,
        "distribution",
        lambda name: SimpleNamespace(
            version="2026.10.2",
            metadata={},
            locate_file=lambda _: pytest.fail("constraints used metadata location"),
        ) if name == "homeassistant" else pytest.fail("unexpected distribution"),
    )
    result = subject.installed_requirements([])
    assert result["core_version"] == "2026.10.2"
    assert result["core_constraints_sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["core_constraint_mismatches"] == []


@pytest.mark.parametrize("origin", [None, "missing/__init__.py"])
def test_missing_active_core_constraints_refused_without_metadata_fallback(
    tmp_path, monkeypatch, origin
):
    monkeypatch.setattr(
        subject.importlib,
        "import_module",
        lambda _: SimpleNamespace(
            __file__=None if origin is None else str(tmp_path / origin)
        ),
    )
    with pytest.raises(ValueError, match="^platform_core_constraints_refused$"):
        subject.active_core_constraints()


def test_actual_zip_synthetic_native_worker_and_production_hash_refusal(
    tmp_path, monkeypatch
):
    payload = build.collect_payload(
        ROOT / "custom_components/homecircle", ROOT / "LICENSE"
    )
    archive, _ = build.write_archive(payload, tmp_path / "release")
    # Installed constraints vary across test hosts. The preceding regression
    # independently checks those; this test exercises the real child and native ABI.
    monkeypatch.setattr(
        subject, "installed_requirements", lambda _: {"core_constraint_mismatches": []}
    )
    result = subject.run_validation(
        archive, expected_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()
    )
    assert result["outcome"] == "passed"
    assert result["synthetic_native_worker"] and result["production_hash_refusal"]
    assert result["worker_processes_reaped"] and result["cleanup_ok"]
    assert result["package_sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert result["evidence_kind"] == "synthetic_native_actual_zip"
    assert result["network_allowed"] is result["apple_binary_executed"] is False
    assert result["owner_data_read"] is False and result["account_requests"] == 0

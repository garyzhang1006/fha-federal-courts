import hashlib
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_inputs import check_manifest
from run_pipeline import json_safe, portable_summary


def _manifest(path, payload):
    digest = hashlib.sha256(payload).hexdigest()
    path.write_text(json.dumps({
        "schema_version": 1,
        "files": [{"path": "input.txt", "bytes": len(payload), "sha256": digest}],
    }))


def test_input_manifest_accepts_exact_file(tmp_path):
    payload = b"frozen\n"
    (tmp_path / "input.txt").write_bytes(payload)
    manifest = tmp_path / "manifest.json"
    _manifest(manifest, payload)
    assert check_manifest(tmp_path, manifest) == []


def test_input_manifest_rejects_changed_file(tmp_path):
    payload = b"frozen\n"
    (tmp_path / "input.txt").write_bytes(payload)
    manifest = tmp_path / "manifest.json"
    _manifest(manifest, payload)
    (tmp_path / "input.txt").write_bytes(b"changed\n")
    failures = check_manifest(tmp_path, manifest)
    assert len(failures) == 1
    assert "mismatch" in failures[0]


def test_input_manifest_rejects_parent_path(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": 1,
        "files": [{"path": "../escape", "bytes": 0, "sha256": ""}],
    }))
    assert check_manifest(tmp_path, manifest) == ["unsafe manifest path: ../escape"]


def test_input_manifest_rejects_wrong_top_level_shape(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    assert check_manifest(tmp_path, manifest) == [
        f"unsupported manifest schema: {manifest}"
    ]


def test_input_manifest_rejects_non_object_entry(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 1, "files": [None]}))
    assert check_manifest(tmp_path, manifest) == [
        "invalid manifest entry 0: expected an object"
    ]


def test_pipeline_summary_converts_nonfinite_values_to_json_null():
    assert json_safe({"coef": float("nan"), "nested": [float("inf"), 8]}) == {
        "coef": None,
        "nested": [None, 8],
    }


def test_pipeline_summary_uses_repo_relative_output_path():
    result = portable_summary({"outputs": str(Path(__file__).parents[1] / "outputs")})
    assert result["outputs"] == "outputs"

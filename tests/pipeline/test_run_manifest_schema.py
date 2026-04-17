from __future__ import annotations


def test_dataset_manifest_has_required_top_level_fields(dataset_manifest: dict) -> None:
    required = {
        "dataset_id",
        "region",
        "status",
        "run_id",
        "generated_at_utc",
        "code_version",
        "config_version",
        "source_manifests",
        "artifacts",
    }
    assert required.issubset(dataset_manifest)


def test_dataset_manifest_status_is_supported(dataset_manifest: dict) -> None:
    assert dataset_manifest["status"] in {"draft", "promoted", "retired"}


def test_dataset_manifest_artifacts_are_mapped(dataset_manifest: dict) -> None:
    artifacts = dataset_manifest["artifacts"]
    assert isinstance(artifacts, dict)
    assert "spots" in artifacts
    assert "segments_high" in artifacts
    assert "gallery" in artifacts

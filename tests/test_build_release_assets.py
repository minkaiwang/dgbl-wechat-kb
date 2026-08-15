from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from build_release_assets import build_release_assets
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
METADATA_BASE_NAME = "dgbl-wechat-metadata-v0.2.0"
FULLTEXT_BASE_NAME = "dgbl-wechat-fulltext-v0.2.0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_assets_are_complete_and_self_describing(tmp_path: Path) -> None:
    result = build_release_assets(ROOT, tmp_path, requested_version="0.2.0")
    expected_names = {
        f"{METADATA_BASE_NAME}.jsonl",
        f"{METADATA_BASE_NAME}.csv",
        f"{METADATA_BASE_NAME}.schema.json",
        f"{METADATA_BASE_NAME}.zip",
        f"{FULLTEXT_BASE_NAME}.jsonl",
        f"{FULLTEXT_BASE_NAME}.schema.json",
        f"{FULLTEXT_BASE_NAME}.zip",
        "SHA256SUMS.txt",
    }
    assert {Path(path).name for path in result["assets"]} == expected_names
    assert result["records"] == 475

    jsonl_rows = [
        json.loads(line)
        for line in (tmp_path / f"{METADATA_BASE_NAME}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(jsonl_rows) == 475
    assert jsonl_rows[0]["position"] == 1
    assert jsonl_rows[-1]["position"] == 475

    assert jsonl_rows[0]["schema_version"] == 2
    assert jsonl_rows[0]["content_rights"] == "CC-BY-NC-4.0"

    csv_text = (tmp_path / f"{METADATA_BASE_NAME}.csv").read_text(encoding="utf-8-sig")
    csv_rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(csv_rows) == 475
    assert csv_rows[0]["article_id"] == jsonl_rows[0]["article_id"]

    schema = json.loads(
        (tmp_path / f"{METADATA_BASE_NAME}.schema.json").read_text(encoding="utf-8")
    )
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(jsonl_rows[0])
    metadata_validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for row in jsonl_rows:
        metadata_validator.validate(row)

    with zipfile.ZipFile(tmp_path / f"{METADATA_BASE_NAME}.zip") as archive:
        names = set(archive.namelist())
        assert f"{METADATA_BASE_NAME}/article-metadata.jsonl" in names
        assert f"{METADATA_BASE_NAME}/article-metadata.csv" in names
        assert f"{METADATA_BASE_NAME}/MANIFEST.json" in names
        package_manifest = json.loads(
            archive.read(f"{METADATA_BASE_NAME}/MANIFEST.json")
        )
        assert package_manifest["record_count"] == 475
        assert package_manifest["metadata_license"] == "CC-BY-4.0"

    fulltext_rows = [
        json.loads(line)
        for line in (tmp_path / f"{FULLTEXT_BASE_NAME}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(fulltext_rows) == 475
    assert fulltext_rows[0]["content_rights"] == "CC-BY-NC-4.0"
    assert fulltext_rows[0]["image_policy"] == "placeholder"
    assert fulltext_rows[0]["body_markdown"]
    fulltext_schema = json.loads(
        (tmp_path / f"{FULLTEXT_BASE_NAME}.schema.json").read_text(encoding="utf-8")
    )
    fulltext_validator = Draft202012Validator(
        fulltext_schema, format_checker=FormatChecker()
    )
    for row in fulltext_rows:
        fulltext_validator.validate(row)

    with zipfile.ZipFile(tmp_path / f"{FULLTEXT_BASE_NAME}.zip") as archive:
        names = set(archive.namelist())
        article_names = {
            name for name in names if name.startswith(f"{FULLTEXT_BASE_NAME}/articles/")
        }
        assert len(article_names) == 475
        assert f"{FULLTEXT_BASE_NAME}/article-fulltext.jsonl" in names
        assert f"{FULLTEXT_BASE_NAME}/TEXT-LICENSE.md" in names
        fulltext_manifest = json.loads(
            archive.read(f"{FULLTEXT_BASE_NAME}/MANIFEST.json")
        )
        assert fulltext_manifest["record_count"] == 475
        assert fulltext_manifest["text_license"] == "CC-BY-NC-4.0"
        assert fulltext_manifest["included_image_files"] == 0

    checksum_lines = (tmp_path / "SHA256SUMS.txt").read_text(encoding="ascii").splitlines()
    checksum_map = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in checksum_lines}
    assert set(checksum_map) == expected_names - {"SHA256SUMS.txt"}
    for name, expected_digest in checksum_map.items():
        assert digest(tmp_path / name) == expected_digest


def test_release_archive_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_release_assets(ROOT, first)
    build_release_assets(ROOT, second)
    for name in (
        f"{METADATA_BASE_NAME}.jsonl",
        f"{METADATA_BASE_NAME}.csv",
        f"{METADATA_BASE_NAME}.schema.json",
        f"{METADATA_BASE_NAME}.zip",
        f"{FULLTEXT_BASE_NAME}.jsonl",
        f"{FULLTEXT_BASE_NAME}.schema.json",
        f"{FULLTEXT_BASE_NAME}.zip",
    ):
        assert digest(first / name) == digest(second / name)
    assert digest(first / "SHA256SUMS.txt") == digest(second / "SHA256SUMS.txt")

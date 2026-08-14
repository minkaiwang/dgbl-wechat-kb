from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from build_release_assets import build_release_assets

ROOT = Path(__file__).resolve().parents[1]
BASE_NAME = "dgbl-wechat-metadata-v0.1.0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_assets_are_complete_and_self_describing(tmp_path: Path) -> None:
    result = build_release_assets(ROOT, tmp_path, requested_version="0.1.0")
    expected_names = {
        f"{BASE_NAME}.jsonl",
        f"{BASE_NAME}.csv",
        f"{BASE_NAME}.schema.json",
        f"{BASE_NAME}.zip",
        "SHA256SUMS.txt",
    }
    assert {Path(path).name for path in result["assets"]} == expected_names
    assert result["records"] == 474

    jsonl_rows = [
        json.loads(line)
        for line in (tmp_path / f"{BASE_NAME}.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(jsonl_rows) == 474
    assert jsonl_rows[0]["position"] == 1
    assert jsonl_rows[-1]["position"] == 474

    csv_text = (tmp_path / f"{BASE_NAME}.csv").read_text(encoding="utf-8-sig")
    csv_rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert len(csv_rows) == 474
    assert csv_rows[0]["article_id"] == jsonl_rows[0]["article_id"]

    schema = json.loads((tmp_path / f"{BASE_NAME}.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(jsonl_rows[0])

    with zipfile.ZipFile(tmp_path / f"{BASE_NAME}.zip") as archive:
        names = set(archive.namelist())
        assert f"{BASE_NAME}/article-metadata.jsonl" in names
        assert f"{BASE_NAME}/article-metadata.csv" in names
        assert f"{BASE_NAME}/MANIFEST.json" in names
        package_manifest = json.loads(archive.read(f"{BASE_NAME}/MANIFEST.json"))
        assert package_manifest["record_count"] == 474
        assert package_manifest["metadata_license"] == "CC-BY-4.0"

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
    for suffix in ("jsonl", "csv", "schema.json", "zip"):
        name = f"{BASE_NAME}.{suffix}"
        assert digest(first / name) == digest(second / name)
    assert digest(first / "SHA256SUMS.txt") == digest(second / "SHA256SUMS.txt")

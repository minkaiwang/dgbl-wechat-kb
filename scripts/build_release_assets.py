from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tempfile
import tomllib
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

import yaml
from kb_common import jsonl_load
from validate_public_release import EXPECTED_ARTICLE_COUNT, validate_public_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_SLUG = "dgbl-wechat-metadata"
CSV_FIELDS = (
    "schema_version",
    "article_id",
    "position",
    "issue_no",
    "title",
    "display_title",
    "series",
    "author",
    "published_at",
    "source_url",
    "content_rights",
    "asset_rights",
)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def release_metadata(root: Path) -> tuple[str, str]:
    with (root / "pyproject.toml").open("rb") as handle:
        project_version = str(tomllib.load(handle)["project"]["version"])
    citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    citation_version = str(citation["version"])
    release_date = str(citation["date-released"])
    if citation_version != project_version:
        raise ValueError(
            f"version mismatch: pyproject={project_version}, CITATION.cff={citation_version}"
        )
    date.fromisoformat(release_date)
    return project_version, release_date


def csv_bytes(rows: list[dict]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field) for field in CSV_FIELDS})
    return buffer.getvalue().encode("utf-8-sig")


def package_readme(version: str, release_date: str) -> str:
    return f"""# 数字游戏学习研究公众号公开元数据 v{version}

- 发布日期：{release_date}
- 记录数：{EXPECTED_ARTICLE_COUNT}
- 数据许可：CC BY 4.0
- 项目地址：https://github.com/minkaiwang/dgbl-wechat-kb

## 文件

- `article-metadata.jsonl`：每行一个 JSON 对象，UTF-8。
- `article-metadata.csv`：UTF-8 with BOM，便于 Excel 直接打开。
- `article-metadata.schema.json`：单条 JSONL 记录的 JSON Schema。
- `MANIFEST.json`：版本、数量、日期范围和栏目统计。
- `DATA-LICENSE.md`：公开元数据与项目文档许可。

本数据包不包含微信文章正文、摘要片段、原始 HTML、图片或私有抓取材料。请使用
`source_url` 回到微信原文核验，并在复用时保留项目署名与来源链接。
"""


def manifest(rows: list[dict], version: str, release_date: str) -> dict:
    issue_numbers = sorted(
        {int(row["issue_no"]) for row in rows if row.get("issue_no") is not None}
    )
    maximum_issue = max(issue_numbers)
    issue_gaps = sorted(set(range(1, maximum_issue + 1)) - set(issue_numbers))
    series_counts = Counter(str(row.get("series") or "未分类") for row in rows)
    author_labels = sorted({str(row.get("author") or "") for row in rows if row.get("author")})
    dates = sorted(str(row["published_at"])[:10] for row in rows)
    return {
        "dataset": "数字游戏学习研究公众号公开元数据",
        "dataset_version": version,
        "schema_version": 1,
        "release_date": release_date,
        "record_count": len(rows),
        "position_range": [int(rows[0]["position"]), int(rows[-1]["position"])],
        "publication_date_range": [dates[0], dates[-1]],
        "maximum_issue_no": maximum_issue,
        "issue_number_gaps": issue_gaps,
        "series_label_counts": dict(sorted(series_counts.items())),
        "author_labels": author_labels,
        "metadata_license": "CC-BY-4.0",
        "source_platform": "WeChat Official Account",
        "excluded_content": [
            "article body",
            "article excerpt",
            "raw HTML",
            "images",
            "private fetch records",
        ],
    }


def deterministic_zip(path: Path, folder: str, entries: dict[str, bytes], release_date: str) -> None:
    year, month, day = (int(value) for value in release_date.split("-"))
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(f"{folder}/{name}", date_time=(year, month, day, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, entries[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_release_assets(root: Path, output: Path, requested_version: str | None = None) -> dict:
    version, release_date = release_metadata(root)
    if requested_version is not None and requested_version != version:
        raise ValueError(f"requested version {requested_version} does not match project version {version}")

    rows = jsonl_load(root / "data" / "article-metadata.jsonl")
    validation_errors = validate_public_metadata(rows, EXPECTED_ARTICLE_COUNT)
    if validation_errors:
        raise ValueError("public metadata validation failed: " + "; ".join(validation_errors))

    schema_payload = (root / "data" / "article-metadata.schema.json").read_bytes()
    schema = json.loads(schema_payload)
    if set(schema["properties"]) != set(CSV_FIELDS):
        raise ValueError("JSON Schema fields do not match the release field list")

    base_name = f"{DATASET_SLUG}-v{version}"
    jsonl_payload = (root / "data" / "article-metadata.jsonl").read_bytes()
    csv_payload = csv_bytes(rows)
    manifest_payload = (
        json.dumps(manifest(rows, version, release_date), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    readme_payload = package_readme(version, release_date).encode("utf-8")
    license_payload = (root / "DATA-LICENSE.md").read_bytes()

    output.mkdir(parents=True, exist_ok=True)
    jsonl_path = output / f"{base_name}.jsonl"
    csv_path = output / f"{base_name}.csv"
    schema_path = output / f"{base_name}.schema.json"
    zip_path = output / f"{base_name}.zip"
    checksums_path = output / "SHA256SUMS.txt"
    atomic_write_bytes(jsonl_path, jsonl_payload)
    atomic_write_bytes(csv_path, csv_payload)
    atomic_write_bytes(schema_path, schema_payload)

    zip_entries = {
        "article-metadata.csv": csv_payload,
        "article-metadata.jsonl": jsonl_payload,
        "article-metadata.schema.json": schema_payload,
        "DATA-LICENSE.md": license_payload,
        "MANIFEST.json": manifest_payload,
        "README.md": readme_payload,
    }
    deterministic_zip(zip_path, base_name, zip_entries, release_date)

    release_assets = [jsonl_path, csv_path, schema_path, zip_path]
    checksums = "".join(
        f"{sha256_bytes(path.read_bytes())}  {path.name}\n" for path in release_assets
    )
    atomic_write_bytes(checksums_path, checksums.encode("ascii"))

    return {
        "version": version,
        "release_date": release_date,
        "records": len(rows),
        "output": str(output),
        "assets": [str(path) for path in [*release_assets, checksums_path]],
        "zip_entries": [f"{base_name}/{name}" for name in sorted(zip_entries)],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build deterministic public dataset release assets")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--version")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = build_release_assets(
        args.root.resolve(), args.output.resolve(), requested_version=args.version
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

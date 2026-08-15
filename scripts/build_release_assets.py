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
from build_fulltext_dataset import FULLTEXT_FIELDS, collect_fulltext, fulltext_jsonl
from kb_common import jsonl_load
from validate_public_release import EXPECTED_ARTICLE_COUNT, validate_public_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_DATASET_SLUG = "dgbl-wechat-metadata"
FULLTEXT_DATASET_SLUG = "dgbl-wechat-fulltext"
CSV_FIELDS = (
    "schema_version",
    "article_id",
    "position",
    "issue_no",
    "title",
    "display_title",
    "series",
    "author",
    "licensor",
    "published_at",
    "source_url",
    "content_rights",
    "content_license_url",
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


def metadata_package_readme(version: str, release_date: str) -> str:
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
`source_url` 回到微信原文核验，并在复用时保留项目署名与来源链接。v0.2.0 起，获授权的
文章正文另见同一 Release 中的全文 JSONL 与全文 ZIP 数据包。
"""


def metadata_manifest(rows: list[dict], version: str, release_date: str) -> dict:
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
        "schema_version": 2,
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


def fulltext_package_readme(version: str, release_date: str) -> str:
    return f"""# 数字游戏学习研究公众号全文知识库 v{version}

- 发布日期：{release_date}
- 文章数：{EXPECTED_ARTICLE_COUNT}
- 原创文字许可：CC BY-NC 4.0
- 图片：未包含，仅保留文字占位符
- 项目地址：https://github.com/minkaiwang/dgbl-wechat-kb

## 文件

- `articles/`：按年份保存的 475 篇 Markdown 正文。
- `article-fulltext.jsonl`：每行一篇文章，正文位于 `body_markdown`。
- `article-fulltext.schema.json`：单条全文 JSONL 记录的 JSON Schema。
- `catalog.md`：可点击的文章目录。
- `llms.txt`：面向检索代理的轻量索引。
- `content-license.json`：授权范围的机器可读记录。
- `TEXT-LICENSE.md`：CC BY-NC 4.0 正文许可与排除范围。
- `MANIFEST.json`：版本、数量、图片占位符和许可统计。

全文许可只覆盖“靓点迷人”拥有或控制著作权的原创文字。论文图表、期刊封面、照片、字体、
商标、视频、第三方引文、原始 HTML 和私有抓取材料均不在数据包中或不在许可范围内。
"""


def fulltext_manifest(rows: list[dict], version: str, release_date: str) -> dict:
    dates = sorted(str(row["published_at"])[:10] for row in rows)
    return {
        "dataset": "数字游戏学习研究公众号全文知识库",
        "dataset_version": version,
        "schema_version": 1,
        "release_date": release_date,
        "record_count": len(rows),
        "position_range": [int(rows[0]["position"]), int(rows[-1]["position"])],
        "publication_date_range": [dates[0], dates[-1]],
        "author": "靓点迷人",
        "licensor": "靓点迷人",
        "text_license": "CC-BY-NC-4.0",
        "metadata_license": "CC-BY-4.0",
        "image_policy": "placeholder",
        "included_image_files": 0,
        "unique_image_source_count": sum(int(row["image_count"]) for row in rows),
        "image_occurrence_count": sum(
            int(row["image_occurrence_count"]) for row in rows
        ),
        "source_platform": "WeChat Official Account",
        "excluded_content": [
            "original images",
            "third-party figures and media",
            "raw HTML",
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

    metadata_base_name = f"{METADATA_DATASET_SLUG}-v{version}"
    fulltext_base_name = f"{FULLTEXT_DATASET_SLUG}-v{version}"
    jsonl_payload = (root / "data" / "article-metadata.jsonl").read_bytes()
    csv_payload = csv_bytes(rows)
    metadata_manifest_payload = (
        json.dumps(metadata_manifest(rows, version, release_date), ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")
    metadata_readme_payload = metadata_package_readme(version, release_date).encode("utf-8")
    license_payload = (root / "DATA-LICENSE.md").read_bytes()

    fulltext_rows = collect_fulltext(root, EXPECTED_ARTICLE_COUNT)
    fulltext_schema_payload = (root / "data" / "article-fulltext.schema.json").read_bytes()
    fulltext_schema = json.loads(fulltext_schema_payload)
    if set(fulltext_schema["properties"]) != set(FULLTEXT_FIELDS):
        raise ValueError("fulltext JSON Schema fields do not match the release field list")
    fulltext_jsonl_payload = fulltext_jsonl(fulltext_rows).encode("utf-8")
    fulltext_manifest_payload = (
        json.dumps(
            fulltext_manifest(fulltext_rows, version, release_date),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")
    fulltext_readme_payload = fulltext_package_readme(version, release_date).encode("utf-8")
    text_license_payload = (root / "TEXT-LICENSE.md").read_bytes()
    content_license_payload = (root / "data" / "content-license.json").read_bytes()

    output.mkdir(parents=True, exist_ok=True)
    jsonl_path = output / f"{metadata_base_name}.jsonl"
    csv_path = output / f"{metadata_base_name}.csv"
    schema_path = output / f"{metadata_base_name}.schema.json"
    zip_path = output / f"{metadata_base_name}.zip"
    fulltext_jsonl_path = output / f"{fulltext_base_name}.jsonl"
    fulltext_schema_path = output / f"{fulltext_base_name}.schema.json"
    fulltext_zip_path = output / f"{fulltext_base_name}.zip"
    checksums_path = output / "SHA256SUMS.txt"
    atomic_write_bytes(jsonl_path, jsonl_payload)
    atomic_write_bytes(csv_path, csv_payload)
    atomic_write_bytes(schema_path, schema_payload)
    atomic_write_bytes(fulltext_jsonl_path, fulltext_jsonl_payload)
    atomic_write_bytes(fulltext_schema_path, fulltext_schema_payload)

    metadata_zip_entries = {
        "article-metadata.csv": csv_payload,
        "article-metadata.jsonl": jsonl_payload,
        "article-metadata.schema.json": schema_payload,
        "DATA-LICENSE.md": license_payload,
        "MANIFEST.json": metadata_manifest_payload,
        "README.md": metadata_readme_payload,
    }
    deterministic_zip(zip_path, metadata_base_name, metadata_zip_entries, release_date)

    fulltext_zip_entries = {
        "article-fulltext.jsonl": fulltext_jsonl_payload,
        "article-fulltext.schema.json": fulltext_schema_payload,
        "catalog.md": (root / "docs" / "catalog.md").read_bytes(),
        "content-license.json": content_license_payload,
        "llms.txt": (root / "docs" / "llms.txt").read_bytes(),
        "MANIFEST.json": fulltext_manifest_payload,
        "README.md": fulltext_readme_payload,
        "TEXT-LICENSE.md": text_license_payload,
    }
    for article_path in sorted((root / "docs" / "articles").rglob("*.md")):
        relative = article_path.relative_to(root / "docs" / "articles").as_posix()
        fulltext_zip_entries[f"articles/{relative}"] = article_path.read_bytes()
    deterministic_zip(
        fulltext_zip_path, fulltext_base_name, fulltext_zip_entries, release_date
    )

    release_assets = [
        jsonl_path,
        csv_path,
        schema_path,
        zip_path,
        fulltext_jsonl_path,
        fulltext_schema_path,
        fulltext_zip_path,
    ]
    checksums = "".join(
        f"{sha256_bytes(path.read_bytes())}  {path.name}\n" for path in release_assets
    )
    atomic_write_bytes(checksums_path, checksums.encode("ascii"))

    return {
        "version": version,
        "release_date": release_date,
        "records": len(rows),
        "fulltext_records": len(fulltext_rows),
        "output": str(output),
        "assets": [str(path) for path in [*release_assets, checksums_path]],
        "metadata_zip_entries": [
            f"{metadata_base_name}/{name}" for name in sorted(metadata_zip_entries)
        ],
        "fulltext_zip_entry_count": len(fulltext_zip_entries),
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

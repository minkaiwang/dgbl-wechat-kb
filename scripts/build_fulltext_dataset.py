from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from kb_common import atomic_write_text, read_markdown_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TEXT_LICENSE = "CC-BY-NC-4.0"
EXPECTED_LICENSOR = "靓点迷人"
EXPECTED_LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
PLACEHOLDER_RE = re.compile(r"^\[图像 \d+：待版权审查，原图保存在私有归档\]$", re.MULTILINE)
EMBEDDED_IMAGE_RE = re.compile(r"!\[[^]]*]\([^)]*\)|<img\b|data:image/", re.IGNORECASE)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
FULLTEXT_FIELDS = (
    "schema_version",
    "article_id",
    "position",
    "issue_no",
    "title",
    "display_title",
    "series",
    "tags",
    "author",
    "licensor",
    "published_at",
    "source_url",
    "markdown_path",
    "text_chars",
    "image_count",
    "image_occurrence_count",
    "image_policy",
    "content_rights",
    "content_license_url",
    "asset_rights",
    "body_markdown",
)


def fulltext_record(path: Path, root: Path) -> dict:
    metadata, body = read_markdown_frontmatter(path)
    relative = path.relative_to(root).as_posix()
    if metadata.get("author") != EXPECTED_LICENSOR:
        raise ValueError(f"unexpected author: {relative}")
    if metadata.get("licensor") != EXPECTED_LICENSOR:
        raise ValueError(f"unexpected licensor: {relative}")
    if metadata.get("content_rights") != EXPECTED_TEXT_LICENSE:
        raise ValueError(f"unexpected text license: {relative}")
    if metadata.get("content_license_url") != EXPECTED_LICENSE_URL:
        raise ValueError(f"unexpected text-license URL: {relative}")
    if metadata.get("asset_rights") != "pending_review":
        raise ValueError(f"unexpected asset-rights state: {relative}")
    if metadata.get("image_policy") != "placeholder":
        raise ValueError(f"unexpected image policy: {relative}")
    if metadata.get("qa_status") != "pass":
        raise ValueError(f"article has not passed QA: {relative}")
    if EMBEDDED_IMAGE_RE.search(body):
        raise ValueError(f"embedded image found: {relative}")
    if EMAIL_RE.search(body):
        raise ValueError(f"email address found: {relative}")
    private_markers = (
        "private-archive/",
        "raw-html/",
        "C:" + "\\Users\\",
        "E:" + "\\DGBL-WeChat-KB",
    )
    for marker in private_markers:
        if marker.lower() in body.lower():
            raise ValueError(f"private path marker found: {relative}")

    occurrence_count = len(PLACEHOLDER_RE.findall(body))
    if occurrence_count != int(metadata.get("image_occurrence_count", -1)):
        raise ValueError(f"image occurrence count does not match placeholders: {relative}")
    if occurrence_count < int(metadata.get("image_count", 0)):
        raise ValueError(f"unique image count exceeds image occurrences: {relative}")

    record = {
        "schema_version": 1,
        "article_id": metadata["article_id"],
        "position": int(metadata["position"]),
        "issue_no": metadata.get("issue_no"),
        "title": metadata["title"],
        "display_title": metadata.get("display_title"),
        "series": metadata.get("series"),
        "tags": metadata.get("tags", []),
        "author": metadata["author"],
        "licensor": metadata["licensor"],
        "published_at": metadata["published_at"],
        "source_url": metadata["source_url"],
        "markdown_path": relative,
        "text_chars": int(metadata["text_chars"]),
        "image_count": int(metadata.get("image_count", 0)),
        "image_occurrence_count": occurrence_count,
        "image_policy": metadata["image_policy"],
        "content_rights": metadata["content_rights"],
        "content_license_url": metadata["content_license_url"],
        "asset_rights": metadata["asset_rights"],
        "body_markdown": body.strip() + "\n",
    }
    if tuple(record) != FULLTEXT_FIELDS:
        raise ValueError(f"fulltext record fields are out of order: {relative}")
    return record


def collect_fulltext(root: Path, expected_count: int = 475) -> list[dict]:
    paths = sorted((root / "docs" / "articles").rglob("*.md"))
    paths = [path for path in paths if path.name != "index.md"]
    rows = [fulltext_record(path, root) for path in paths]
    rows.sort(key=lambda row: int(row["position"]))
    if len(rows) != expected_count:
        raise ValueError(f"fulltext record count is {len(rows)}; expected {expected_count}")
    if [row["position"] for row in rows] != list(range(1, expected_count + 1)):
        raise ValueError("fulltext positions are not the ordered consecutive range")
    ids = [str(row["article_id"]) for row in rows]
    urls = [str(row["source_url"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate fulltext article IDs found")
    if len(urls) != len(set(urls)):
        raise ValueError("duplicate fulltext source URLs found")
    return rows


def fulltext_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def run(root: Path, output: Path, expected_count: int) -> dict:
    rows = collect_fulltext(root.resolve(), expected_count)
    payload = fulltext_jsonl(rows)
    atomic_write_text(output.resolve(), payload)
    return {
        "records": len(rows),
        "bytes": len(payload.encode("utf-8")),
        "output": str(output.resolve()),
        "text_license": EXPECTED_TEXT_LICENSE,
        "unique_image_count": sum(int(row["image_count"]) for row in rows),
        "image_occurrence_count": sum(int(row["image_occurrence_count"]) for row in rows),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the licensed fulltext JSONL dataset")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--output", type=Path, default=PROJECT_ROOT / "output" / "article-fulltext.jsonl"
    )
    parser.add_argument("--expected-count", type=int, default=475)
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    print(
        json.dumps(
            run(args.root, args.output, args.expected_count), ensure_ascii=False, indent=2
        )
    )

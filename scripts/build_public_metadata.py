from __future__ import annotations

import argparse
import json
from pathlib import Path

from kb_common import atomic_write_text, jsonl_load

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FIELDS = (
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
REQUIRED_FIELDS = ("article_id", "position", "title", "published_at", "source_url")


def public_metadata(row: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if row.get(field) in (None, "")]
    if missing:
        raise ValueError(f"metadata row is missing required fields: {', '.join(missing)}")
    source_url = str(row["source_url"])
    if not source_url.startswith("https://mp.weixin.qq.com/"):
        raise ValueError(f"unexpected source URL for {row['article_id']}: {source_url}")
    return {"schema_version": 2, **{field: row.get(field) for field in PUBLIC_FIELDS}}


def build_public_metadata(input_path: Path, output_path: Path) -> list[dict]:
    rows = [public_metadata(row) for row in jsonl_load(input_path)]
    rows.sort(key=lambda row: int(row["position"]))
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    atomic_write_text(output_path, payload)
    return rows


def public_catalog(rows: list[dict]) -> str:
    lines = [
        "# 公开文章目录",
        "",
        f"当前收录 **{len(rows)}** 篇文章全文与对应微信原文链接。公开 Markdown 不包含原图。",
        "",
        "| 日期 | 栏目 | 全文 | 原文 |",
        "|---|---|---|---|",
    ]
    for row in reversed(rows):
        title = str(row["display_title"] or row["title"]).replace("|", "\\|")
        series = str(row["series"] or "未分类").replace("|", "\\|")
        year = str(row["published_at"])[:4]
        local_path = f"articles/{year}/{int(row['position']):04d}-{row['article_id']}.md"
        lines.append(
            f"| {str(row['published_at'])[:10]} | {series} | [{title}]({local_path}) | "
            f"[微信原文]({row['source_url']}) |"
        )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a rights-safe metadata index and article catalog"
    )
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "articles.jsonl")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "article-metadata.jsonl",
    )
    parser.add_argument(
        "--catalog-output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "catalog-public.md",
    )
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = build_public_metadata(args.input.resolve(), args.output.resolve())
    atomic_write_text(args.catalog_output.resolve(), public_catalog(result))
    print(
        json.dumps(
            {
                "articles": len(result),
                "metadata_output": str(args.output),
                "catalog_output": str(args.catalog_output),
            },
            ensure_ascii=False,
        )
    )

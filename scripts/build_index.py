from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from kb_common import atomic_write_text, jsonl_dump, read_markdown_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def plain_text(markdown: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", markdown, flags=re.IGNORECASE)
    value = re.sub(r"```.*?```", " ", value, flags=re.DOTALL)
    value = re.sub(r"!\[[^]]*]\([^)]*\)", " ", value)
    value = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", value)
    value = re.sub(r"^[#>*+\-]+\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"[`*_~]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def collect_articles(public_root: Path) -> list[dict]:
    rows: list[dict] = []
    article_root = public_root / "docs" / "articles"
    for path in sorted(article_root.glob("**/*.md")):
        if path.name == "index.md":
            continue
        metadata, body = read_markdown_frontmatter(path)
        if not metadata.get("article_id"):
            continue
        text = plain_text(body)
        relative = path.relative_to(public_root).as_posix()
        rows.append(
            {
                "article_id": metadata["article_id"],
                "position": int(metadata["position"]),
                "issue_no": metadata.get("issue_no"),
                "title": metadata["title"],
                "display_title": metadata.get("display_title", metadata["title"]),
                "published_at": metadata["published_at"],
                "series": metadata.get("series", "未分类"),
                "tags": metadata.get("tags", []),
                "author": metadata.get("author", ""),
                "source_url": metadata["source_url"],
                "markdown_path": relative,
                "text_chars": int(metadata.get("text_chars", len(text))),
                "image_count": int(metadata.get("image_count", 0)),
                "image_occurrence_count": int(metadata.get("image_occurrence_count", 0)),
                "content_rights": metadata.get("content_rights", "pending_owner_review"),
                "content_license_url": metadata.get("content_license_url", ""),
                "licensor": metadata.get("licensor", ""),
                "asset_rights": metadata.get("asset_rights", "pending_review"),
                "qa_status": metadata.get("qa_status", "pending"),
                "preview": text[:240].rstrip(),
            }
        )
    rows.sort(key=lambda row: (row["published_at"], row["position"]), reverse=True)
    return rows


def build_catalog(rows: list[dict]) -> str:
    lines = [
        "# 文章目录",
        "",
        f"当前已导入 **{len(rows)}** 篇。目录由 `scripts/build_index.py` 自动生成。",
        "",
        "| 日期 | 栏目 | 文章 | 原文 |",
        "|---|---|---|---|",
    ]
    for row in rows:
        doc_path = Path(row["markdown_path"])
        link = doc_path.relative_to("docs").as_posix()
        title = str(row["display_title"]).replace("|", "\\|")
        series = str(row["series"]).replace("|", "\\|")
        lines.append(
            f"| {str(row['published_at'])[:10]} | {series} | [{title}]({link}) | "
            f"[微信]({row['source_url']}) |"
        )
    return "\n".join(lines) + "\n"


def build_llms_index(rows: list[dict]) -> str:
    lines = [
        "# 数字游戏学习研究公众号知识库",
        "",
        "本文件是面向检索代理的文章索引。正文位于对应 Markdown 路径，引用时应同时给出微信原文链接。",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"## {row['display_title']}",
                f"- 日期: {str(row['published_at'])[:10]}",
                f"- 栏目: {row['series']}",
                f"- 本地: {row['markdown_path']}",
                f"- 原文: {row['source_url']}",
                f"- 摘要片段: {str(row['preview']).rstrip()}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def run(public_root: Path) -> list[dict]:
    root = public_root.resolve()
    rows = collect_articles(root)
    jsonl_dump(rows, root / "data" / "articles.jsonl")
    atomic_write_text(root / "docs" / "catalog.md", build_catalog(rows))
    atomic_write_text(root / "docs" / "llms.txt", build_llms_index(rows))
    print(json.dumps({"indexed": len(rows)}, ensure_ascii=False))
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build public article indexes")
    parser.add_argument("--public-root", type=Path, default=PROJECT_ROOT)
    return parser


if __name__ == "__main__":
    run(build_parser().parse_args().public_root)

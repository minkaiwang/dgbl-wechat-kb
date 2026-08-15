from __future__ import annotations

from pathlib import Path

import pytest
from build_fulltext_dataset import collect_fulltext, fulltext_jsonl


def write_article(root: Path, *, body: str = "正文内容足够长。" * 20) -> None:
    path = root / "docs" / "articles" / "2026" / "0001-wx-123-1.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"""---
title: 示例
display_title: 示例
published_at: '2026-01-01T08:00:00+08:00'
author: 靓点迷人
licensor: 靓点迷人
source_url: https://mp.weixin.qq.com/s?__biz=x&mid=123&idx=1&sn=x
article_id: wx-123-1
position: 1
issue_no: 1
series: 数字游戏学习
tags:
- 数字游戏学习
text_chars: 120
content_rights: CC-BY-NC-4.0
content_license_url: https://creativecommons.org/licenses/by-nc/4.0/
asset_rights: pending_review
image_policy: placeholder
image_count: 1
image_occurrence_count: 1
qa_status: pass
---

[图像 01：待版权审查，原图保存在私有归档]

{body}
""",
        encoding="utf-8",
    )


def test_collect_fulltext_builds_licensed_record(tmp_path: Path) -> None:
    write_article(tmp_path)
    rows = collect_fulltext(tmp_path, expected_count=1)

    assert rows[0]["content_rights"] == "CC-BY-NC-4.0"
    assert rows[0]["image_occurrence_count"] == 1
    assert rows[0]["markdown_path"] == "docs/articles/2026/0001-wx-123-1.md"
    assert "正文内容" in fulltext_jsonl(rows)


def test_collect_fulltext_rejects_embedded_images(tmp_path: Path) -> None:
    write_article(tmp_path, body="![图](https://example.com/image.png)")
    with pytest.raises(ValueError, match="embedded image"):
        collect_fulltext(tmp_path, expected_count=1)

from __future__ import annotations

import json
from pathlib import Path

import pytest
from apply_text_license import LICENSED_NOTE, apply_license
from kb_common import read_markdown_frontmatter


def write_fixture(root: Path, *, author: str = "靓点迷人", body_extra: str = "") -> Path:
    article = root / "docs" / "articles" / "2026" / "0001-wx-123-1.md"
    article.parent.mkdir(parents=True)
    article.write_text(
        f"""---
title: 示例
display_title: 示例
published_at: '2026-01-01T08:00:00+08:00'
account_name: 数字游戏学习研究
author: {author}
source_url: https://mp.weixin.qq.com/s?__biz=x&mid=123&idx=1&sn=x
article_id: wx-123-1
position: 1
issue_no: 1
series: 数字游戏学习
tags:
- 数字游戏学习
content_rights: pending_owner_review
asset_rights: pending_review
image_policy: placeholder
image_count: 1
qa_status: pass
---

# 示例

!!! note "归档说明"
    本页由公开文章自动转换生成。图片暂不进入公开仓库，待逐项完成版权审查。

[图像 01：待版权审查，原图保存在私有归档]

正文。{body_extra}
""",
        encoding="utf-8",
    )
    manifest = {
        "account_name": "数字游戏学习研究",
        "licensor_credit": "靓点迷人",
        "license": "CC-BY-NC-4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc/4.0/",
        "scope": {"position_min": 1, "position_max": 1, "article_count": 1},
    }
    (root / "data").mkdir()
    (root / "data" / "content-license.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    return article


def test_apply_license_updates_frontmatter_note_and_image_occurrences(tmp_path: Path) -> None:
    article = write_fixture(tmp_path)
    result = apply_license(
        tmp_path, tmp_path / "data" / "content-license.json", write=True
    )
    metadata, body = read_markdown_frontmatter(article)

    assert result["articles"] == result["changed"] == 1
    assert metadata["content_rights"] == "CC-BY-NC-4.0"
    assert metadata["licensor"] == "靓点迷人"
    assert metadata["image_occurrence_count"] == 1
    assert LICENSED_NOTE in body


def test_apply_license_rejects_wrong_author(tmp_path: Path) -> None:
    write_fixture(tmp_path, author="其他作者")
    with pytest.raises(ValueError, match="author does not match"):
        apply_license(tmp_path, tmp_path / "data" / "content-license.json", write=False)


def test_apply_license_rejects_contact_information(tmp_path: Path) -> None:
    write_fixture(tmp_path, body_extra=" contact@example.com")
    with pytest.raises(ValueError, match="email address"):
        apply_license(tmp_path, tmp_path / "data" / "content-license.json", write=False)

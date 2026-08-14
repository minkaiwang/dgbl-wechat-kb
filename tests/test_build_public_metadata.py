from __future__ import annotations

from build_public_metadata import public_catalog, public_metadata


def test_public_metadata_excludes_article_text_and_local_paths() -> None:
    result = public_metadata(
        {
            "article_id": "wx-123-1",
            "position": 1,
            "issue_no": 1,
            "title": "[数字游戏学习 1] 示例",
            "display_title": "示例",
            "series": "数字游戏学习",
            "author": "作者",
            "published_at": "2024-07-11T17:33:47+08:00",
            "source_url": "https://mp.weixin.qq.com/s?__biz=abc&mid=123&idx=1&sn=x",
            "content_rights": "pending_owner_review",
            "asset_rights": "pending_review",
            "preview": "不得进入公开元数据的正文片段",
            "markdown_path": "docs/articles/2024/example.md",
            "text_chars": 999,
        }
    )

    assert result["schema_version"] == 1
    assert result["article_id"] == "wx-123-1"
    assert "preview" not in result
    assert "markdown_path" not in result
    assert "text_chars" not in result


def test_public_catalog_links_only_to_wechat_source() -> None:
    row = public_metadata(
        {
            "article_id": "wx-123-1",
            "position": 1,
            "issue_no": 1,
            "title": "[数字游戏学习 1] 示例",
            "display_title": "示例",
            "series": "数字游戏学习",
            "author": "作者",
            "published_at": "2024-07-11T17:33:47+08:00",
            "source_url": "https://mp.weixin.qq.com/s?__biz=abc&mid=123&idx=1&sn=x",
            "content_rights": "pending_owner_review",
            "asset_rights": "pending_review",
        }
    )

    result = public_catalog([row])

    assert "[微信原文](https://mp.weixin.qq.com/" in result
    assert "docs/articles" not in result
    assert "摘要片段" not in result

from __future__ import annotations

from build_index import build_llms_index


def test_llms_preview_does_not_leave_trailing_whitespace() -> None:
    result = build_llms_index(
        [
            {
                "display_title": "示例",
                "published_at": "2026-08-15T00:00:00+08:00",
                "series": "数字游戏学习",
                "markdown_path": "docs/articles/2026/example.md",
                "source_url": "https://mp.weixin.qq.com/example",
                "preview": "恰好在截断位置留下空格 ",
            }
        ]
    )

    assert all(line == line.rstrip() for line in result.splitlines())

from __future__ import annotations

from bs4 import BeautifulSoup
from import_articles import comparable_title, is_allowed_image_url, prepare_content


def test_title_comparison_ignores_punctuation_and_spacing() -> None:
    left = comparable_title("[数字游戏学习 482] 一颗会变色的球，能映照职场适应吗？")
    right = comparable_title("[数字游戏学习 482] 一颗会变色的球, 能映照职场适应吗?")
    assert left == right


def test_public_content_uses_image_placeholder() -> None:
    soup = BeautifulSoup(
        '<div id="js_content"><p>正文内容</p><img data-src="https://mmbiz.qpic.cn/a/0?wx_fmt=png"></div>',
        "html.parser",
    )
    markdown, urls, text_chars = prepare_content(soup.select_one("#js_content"), "placeholder")
    assert "待版权审查" in markdown
    assert "mmbiz.qpic.cn" not in markdown
    assert urls == ["https://mmbiz.qpic.cn/a/0?wx_fmt=png"]
    assert text_chars > 0


def test_image_download_allow_list() -> None:
    assert is_allowed_image_url("https://mmbiz.qpic.cn/path/image.png")
    assert not is_allowed_image_url("https://example.com/image.png")

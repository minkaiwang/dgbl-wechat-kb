from __future__ import annotations

from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup
from import_articles import (
    ArticleImportError,
    comparable_title,
    fetch_bytes_with_curl,
    is_allowed_image_url,
    prepare_content,
)


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


def test_curl_fallback_uses_argument_list_and_https_only(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout=b"article", stderr=b"")

    monkeypatch.setattr("import_articles.shutil.which", lambda _: "curl")
    monkeypatch.setattr("import_articles.subprocess.run", fake_run)

    payload = fetch_bytes_with_curl(
        "https://mp.weixin.qq.com/s?mid=123&idx=1",
        timeout=30,
        retries=3,
    )

    assert payload == b"article"
    assert commands[0][-2:] == ["--url", "https://mp.weixin.qq.com/s?mid=123&idx=1"]
    assert ["--max-filesize", str(30 * 1024 * 1024)] == commands[0][
        commands[0].index("--max-filesize") : commands[0].index("--max-filesize") + 2
    ]
    assert "--location" not in commands[0]


def test_curl_fallback_rejects_non_wechat_hosts() -> None:
    with pytest.raises(ArticleImportError, match="拒绝非微信 HTTPS 地址"):
        fetch_bytes_with_curl("https://example.com/article", timeout=30, retries=1)

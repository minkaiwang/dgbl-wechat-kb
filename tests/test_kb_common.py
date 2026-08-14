from __future__ import annotations

from kb_common import canonical_wechat_url, parse_title


def test_canonical_wechat_url_keeps_validation_fields() -> None:
    value = (
        "http://mp.weixin.qq.com/s?__biz=abc%3D%3D&mid=123&idx=1&sn=xyz&chksm=important&scene=27#rd"
    )
    result = canonical_wechat_url(value)
    assert result.startswith("https://mp.weixin.qq.com/s?")
    assert "chksm=important" in result
    assert "scene=" not in result
    assert "#" not in result


def test_parse_numbered_and_unnumbered_titles() -> None:
    assert parse_title("[数字游戏学习 482] 标题") == ("数字游戏学习", 482, "标题")
    assert parse_title("无栏目标题") == ("未分类", None, "无栏目标题")

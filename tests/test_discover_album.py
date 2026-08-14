from __future__ import annotations

from discover_album import has_more_pages, normalize_article


def test_continue_flag_accepts_wechat_string() -> None:
    assert has_more_pages("1")
    assert has_more_pages(1)
    assert not has_more_pages("0")


def test_normalize_article_preserves_chksm() -> None:
    row = normalize_article(
        {
            "title": "[数字游戏学习 7] 示例",
            "msgid": "123",
            "itemidx": "1",
            "pos_num": "6",
            "create_time": "1720690427",
            "url": "http://mp.weixin.qq.com/s?__biz=abc&mid=123&idx=1&sn=x&chksm=y#rd",
        },
        biz="abc",
        album_id="album",
        account_name="账号",
        discovered_at="now",
    )
    assert row["issue_no"] == 7
    assert row["position"] == 6
    assert "chksm=y" in row["source_url"]

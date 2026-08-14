from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from kb_common import (
    WECHAT_UA,
    atomic_write_json,
    atomic_write_text,
    canonical_wechat_url,
    format_timestamp,
    jsonl_dump,
    parse_title,
    stable_article_id,
)

ENDPOINT = "https://mp.weixin.qq.com/mp/appmsgalbum"


def has_more_pages(value: object) -> bool:
    """WeChat currently serializes continue_flag as a string."""
    return str(value) == "1"


def fetch_page(params: dict[str, str | int], retries: int = 3) -> dict:
    url = f"{ENDPOINT}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "User-Agent": WECHAT_UA,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
            data = json.loads(payload)
            if data.get("base_resp", {}).get("ret", 0) not in (0, None):
                raise RuntimeError(f"WeChat API error: {data.get('base_resp')}")
            return data
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def normalize_article(
    item: dict,
    *,
    biz: str,
    album_id: str,
    account_name: str,
    discovered_at: str,
) -> dict:
    title = str(item.get("title", "")).strip()
    series, issue_no, display_title = parse_title(title)
    msgid = str(item.get("msgid", ""))
    itemidx = str(item.get("itemidx", ""))
    return {
        "id": stable_article_id(msgid, itemidx),
        "position": int(item.get("pos_num", 0)),
        "title": title,
        "display_title": display_title,
        "series": series,
        "issue_no": issue_no,
        "published_at": format_timestamp(item.get("create_time")),
        "create_time": int(item.get("create_time", 0)),
        "account_name": account_name,
        "biz": biz,
        "album_id": album_id,
        "msgid": msgid,
        "itemidx": itemidx,
        "source_url": canonical_wechat_url(str(item.get("url", ""))),
        "cover_url": str(item.get("cover_img_1_1", "")),
        "discovered_at": discovered_at,
        "discovery_source": "wechat_public_album",
        "ingest_status": "discovered",
        "content_rights": "pending_owner_review",
        "asset_rights": "pending_review",
    }


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    lines: list[str] = []
    if fields:
        import io

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        lines.append(buffer.getvalue())
    atomic_write_text(path, "".join(lines))


def discover(args: argparse.Namespace) -> list[dict]:
    snapshot_dir = args.snapshot_dir.resolve()
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    discovered_at = datetime.now(UTC).isoformat(timespec="seconds")
    rows_by_id: dict[str, dict] = {}
    begin_msgid = ""
    begin_itemidx = ""
    seen_cursors: set[tuple[str, str]] = set()

    for page_number in range(1, args.max_pages + 1):
        params: dict[str, str | int] = {
            "action": "getalbum",
            "__biz": args.biz,
            "album_id": args.album_id,
            "count": args.page_size,
            "is_reverse": 1,
            "f": "json",
        }
        if begin_msgid:
            params["begin_msgid"] = begin_msgid
            params["begin_itemidx"] = begin_itemidx

        payload = fetch_page(params, retries=args.retries)
        atomic_write_json(snapshot_dir / f"page-{page_number:04d}.json", payload)
        response = payload.get("getalbum_resp", {})
        items = response.get("article_list", []) or []
        if not items:
            print(f"page={page_number} items=0 stop=empty")
            break

        for item in items:
            row = normalize_article(
                item,
                biz=args.biz,
                album_id=args.album_id,
                account_name=args.account_name,
                discovered_at=discovered_at,
            )
            rows_by_id[row["id"]] = row

        last = items[-1]
        next_cursor = (str(last.get("msgid", "")), str(last.get("itemidx", "")))
        print(
            f"page={page_number} items={len(items)} total={len(rows_by_id)} "
            f"positions={items[0].get('pos_num')}-{items[-1].get('pos_num')} "
            f"continue={response.get('continue_flag')}"
        )

        if not has_more_pages(response.get("continue_flag")):
            break
        if next_cursor in seen_cursors or not all(next_cursor):
            raise RuntimeError(f"Pagination cursor did not advance: {next_cursor}")
        seen_cursors.add(next_cursor)
        begin_msgid, begin_itemidx = next_cursor
        time.sleep(args.delay)
    else:
        raise RuntimeError(f"Reached --max-pages={args.max_pages} before completion")

    rows = sorted(rows_by_id.values(), key=lambda row: (row["position"], row["id"]))
    jsonl_dump(rows, args.output_jsonl.resolve())
    write_csv(rows, args.output_csv.resolve())
    summary = {
        "account_name": args.account_name,
        "biz": args.biz,
        "album_id": args.album_id,
        "article_count": len(rows),
        "first_position": rows[0]["position"] if rows else None,
        "last_position": rows[-1]["position"] if rows else None,
        "discovered_at": discovered_at,
    }
    atomic_write_json(args.summary.resolve(), summary)
    print(json.dumps(summary, ensure_ascii=False))
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discover a public WeChat article album")
    parser.add_argument("--biz", required=True, help="Public __biz account identifier")
    parser.add_argument("--album-id", required=True, help="Public album identifier")
    parser.add_argument("--account-name", default="数字游戏学习研究")
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=20, choices=range(1, 21))
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--retries", type=int, default=3)
    return parser


if __name__ == "__main__":
    discover(build_parser().parse_args())

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from import_articles import (
    DESKTOP_UA,
    backup_images,
    extract_page,
    image_url,
    select_inventory,
)
from kb_common import jsonl_dump, jsonl_load

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(args: argparse.Namespace) -> int:
    inventory = jsonl_load(args.inventory.resolve())
    selected = select_inventory(inventory, args)
    private_root = args.private_root.resolve()
    status_path = private_root / "indexes" / "image-archive-status.jsonl"
    existing = jsonl_load(status_path) if status_path.exists() else []
    status = {str(row["id"]): row for row in existing}
    failed = 0
    headers = {
        "User-Agent": DESKTOP_UA,
        "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=args.timeout) as client:
        for row in selected:
            article_id = str(row["id"])
            year = str(row["published_at"])[:4] or "unknown"
            raw_path = private_root / "raw-html" / year / f"{article_id}.html"
            if not raw_path.exists():
                failed += 1
                status[article_id] = {
                    "id": article_id,
                    "position": row["position"],
                    "status": "missing_html",
                    "image_count": 0,
                    "archived_count": 0,
                    "error": "Raw HTML has not been imported",
                }
            else:
                try:
                    soup = BeautifulSoup(raw_path.read_text(encoding="utf-8"), "html.parser")
                    _, _, _, content = extract_page(soup)
                    urls: list[str] = []
                    seen: set[str] = set()
                    for img in content.find_all("img"):
                        url = image_url(img)
                        if url and url not in seen:
                            seen.add(url)
                            urls.append(url)
                    manifest = backup_images(
                        client,
                        urls,
                        article_id,
                        private_root,
                        args.retries,
                        args.overwrite,
                    )
                    archived = sum(
                        1 for item in manifest if item.get("status") == "archived_private"
                    )
                    failed_items = sum(1 for item in manifest if item.get("status") == "failed")
                    status[article_id] = {
                        "id": article_id,
                        "position": row["position"],
                        "status": "complete" if failed_items == 0 else "partial",
                        "image_count": len(urls),
                        "archived_count": archived,
                        "error": ""
                        if failed_items == 0
                        else f"{failed_items} image downloads failed",
                    }
                    if failed_items:
                        failed += 1
                    print(
                        f"position={row['position']} id={article_id} "
                        f"images={len(urls)} archived={archived} failed={failed_items}"
                    )
                except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
                    failed += 1
                    status[article_id] = {
                        "id": article_id,
                        "position": row["position"],
                        "status": "failed",
                        "image_count": 0,
                        "archived_count": 0,
                        "error": str(exc),
                    }
            jsonl_dump(
                sorted(status.values(), key=lambda item: (int(item["position"]), item["id"])),
                status_path,
            )
            if args.delay > 0:
                time.sleep(args.delay)
    print(json.dumps({"selected": len(selected), "failed": failed}, ensure_ascii=False))
    return 1 if failed and args.fail_on_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive article images to the private layer")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--positions", help="Comma-separated album positions")
    parser.add_argument("--start-position", type=int, default=1)
    parser.add_argument("--end-position", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--fail-on-error", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))

from __future__ import annotations

import argparse
import difflib
import html
import json
import mimetypes
import re
import shutil
import subprocess
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlsplit

import httpx
import markdownify
import yaml
from bs4 import BeautifulSoup, Comment, Tag
from kb_common import (
    atomic_write_json,
    atomic_write_text,
    canonical_wechat_url,
    jsonl_dump,
    jsonl_load,
    sha256_bytes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_IMAGE_HOST_SUFFIXES = (".qpic.cn", ".qlogo.cn", "mp.weixin.qq.com")
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_ARTICLE_BYTES = 30 * 1024 * 1024
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


class ArticleImportError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def fetch_bytes(client: httpx.Client, url: str, retries: int) -> bytes:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.content
        except (httpx.HTTPError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(attempt * 2)
    raise ArticleImportError(f"下载失败（重试 {retries} 次）：{last_error}")


def fetch_bytes_with_curl(url: str, *, timeout: float, retries: int) -> bytes:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != "mp.weixin.qq.com":
        raise ArticleImportError(f"curl 回退拒绝非微信 HTTPS 地址：{url}")
    executable = shutil.which("curl")
    if not executable:
        raise ArticleImportError("系统未安装 curl")
    result = subprocess.run(
        [
            executable,
            "-q",
            "--fail",
            "--silent",
            "--show-error",
            "--compressed",
            "--proto",
            "=https",
            "--max-filesize",
            str(MAX_ARTICLE_BYTES),
            "--max-time",
            str(max(1, int(timeout))),
            "--retry",
            str(max(0, retries - 1)),
            "--user-agent",
            DESKTOP_UA,
            "--header",
            "Accept-Language: zh-CN,zh;q=0.9",
            "--referer",
            "https://mp.weixin.qq.com/",
            "--url",
            url,
        ],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ArticleImportError(f"curl 下载失败（退出码 {result.returncode}）：{error}")
    if len(result.stdout) > MAX_ARTICLE_BYTES:
        raise ArticleImportError(f"curl 返回内容超过 {MAX_ARTICLE_BYTES} 字节上限")
    return result.stdout


def is_article_html(payload: bytes) -> bool:
    soup = BeautifulSoup(payload.decode("utf-8", errors="replace"), "html.parser")
    return (
        soup.select_one("#activity-name") is not None and soup.select_one("#js_content") is not None
    )


def comparable_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", normalize_space(value)).lower()
    return "".join(char for char in normalized if char.isalnum() or "\u4e00" <= char <= "\u9fff")


def resolve_sogou_article(client: httpx.Client, expected_title: str, retries: int) -> bytes:
    query = re.sub(r"^\[[^\]]+\]\s*", "", expected_title).strip()
    query = re.sub(r"[，。！？、；：,.!?;:（）()《》【】]", " ", query)
    query = normalize_space(query)[:180]
    search_url = f"https://weixin.sogou.com/weixin?type=2&query={quote(query)}"
    search_bytes = fetch_bytes(client, search_url, retries)
    search_html = search_bytes.decode("utf-8", errors="replace")
    if "请输入验证码" in search_html or "antispider" in search_html:
        raise ArticleImportError("搜狗微信搜索触发验证码")
    soup = BeautifulSoup(search_html, "html.parser")
    expected = comparable_title(expected_title)
    candidates: list[tuple[float, Tag]] = []
    for anchor in soup.select("ul.news-list li .txt-box h3 a[href]"):
        actual = comparable_title(anchor.get_text(" ", strip=True))
        score = difflib.SequenceMatcher(a=expected, b=actual).ratio()
        candidates.append((score, anchor))
    if not candidates:
        raise ArticleImportError("搜狗微信搜索未返回文章候选项")
    score, anchor = max(candidates, key=lambda item: item[0])
    if score < 0.72:
        raise ArticleImportError(f"搜狗微信搜索无可靠标题匹配，最高相似度 {score:.3f}")

    redirect_url = urljoin(search_url, str(anchor["href"]))
    redirect_bytes = fetch_bytes(client, redirect_url, retries)
    redirect_html = redirect_bytes.decode("utf-8", errors="replace")
    approval = re.search(r"\.src\s*=\s*'([^']+)'\s*\+\s*'([^']+)'", redirect_html)
    if approval:
        try:
            client.get(approval.group(1) + approval.group(2))
        except httpx.HTTPError:
            pass
    parts = re.findall(r"url\s*\+=\s*'([^']*)'", redirect_html)
    signed_url = "".join(parts).replace("@", "").replace("\\x26", "&").replace("\\/", "/")
    if not signed_url.startswith("https://mp.weixin.qq.com/s?"):
        raise ArticleImportError("无法解析搜狗微信搜索的临时文章链接")
    article_bytes = fetch_bytes(client, signed_url, retries)
    if not is_article_html(article_bytes):
        raise ArticleImportError("搜狗临时链接未返回完整文章正文")
    return article_bytes


def fetch_article_page(
    client: httpx.Client,
    row: dict,
    retries: int,
    use_sogou_fallback: bool,
    use_curl_fallback: bool,
    timeout: float,
) -> tuple[bytes, str]:
    direct_errors: list[str] = []
    source_url = canonical_wechat_url(str(row["source_url"]))
    try:
        direct = fetch_bytes(client, source_url, retries)
        if is_article_html(direct):
            return direct, "wechat_direct"
        direct_errors.append("httpx 直链返回验证页")
    except ArticleImportError as exc:
        direct_errors.append(str(exc))
    if use_curl_fallback:
        try:
            curl_direct = fetch_bytes_with_curl(source_url, timeout=timeout, retries=retries)
            if is_article_html(curl_direct):
                return curl_direct, "curl_direct"
            direct_errors.append("curl 直链返回验证页")
        except ArticleImportError as exc:
            direct_errors.append(str(exc))
    if not use_sogou_fallback:
        raise ArticleImportError("；".join(direct_errors) or "微信直链未返回完整文章")
    try:
        return resolve_sogou_article(client, str(row["title"]), retries), "sogou_signed_link"
    except ArticleImportError as exc:
        direct_error = "；".join(direct_errors) or "微信直链未返回完整文章"
        raise ArticleImportError(f"{direct_error}；搜狗回退失败：{exc}") from exc


def extract_page(soup: BeautifulSoup) -> tuple[str, str, str, Tag]:
    title_node = soup.select_one("#activity-name")
    account_node = soup.select_one("#js_name")
    author_node = soup.select_one("#js_author_name")
    content = soup.select_one("#js_content")
    title = normalize_space(title_node.get_text(" ", strip=True)) if title_node else ""
    account = normalize_space(account_node.get_text(" ", strip=True)) if account_node else ""
    author = normalize_space(author_node.get_text(" ", strip=True)) if author_node else ""
    if not title or content is None:
        page_text = normalize_space(soup.get_text(" ", strip=True))
        hint = page_text[:160] if page_text else "空页面"
        raise ArticleImportError(f"未找到标题或正文，可能遇到验证页：{hint}")
    return title, account, author, content


def image_url(img: Tag) -> str:
    value = str(img.get("data-src") or img.get("src") or "").strip()
    value = html.unescape(value)
    if value.startswith("//"):
        value = f"https:{value}"
    return value


def is_allowed_image_url(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    return parts.scheme == "https" and any(
        host == suffix.lstrip(".") or host.endswith(suffix)
        for suffix in ALLOWED_IMAGE_HOST_SUFFIXES
    )


def infer_extension(url: str, content_type: str) -> str:
    query_format = parse_qs(urlsplit(url).query).get("wx_fmt", [""])[0].lower()
    aliases = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp"}
    if query_format in aliases:
        return aliases[query_format]
    guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ".bin"
    return ".jpg" if guessed == ".jpe" else guessed


def backup_images(
    client: httpx.Client,
    urls: list[str],
    article_id: str,
    private_root: Path,
    retries: int,
    overwrite: bool,
) -> list[dict]:
    image_dir = private_root / "original-assets" / article_id
    manifest_path = image_dir / "manifest.json"
    if manifest_path.exists() and not overwrite:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(existing, list) and len(existing) == len(urls):
            return existing

    image_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    for index, url in enumerate(urls, start=1):
        record: dict = {"index": index, "source_url": url, "status": "pending"}
        if not is_allowed_image_url(url):
            record.update(status="skipped_untrusted_host", error="Host is outside the allow-list")
            manifest.append(record)
            continue
        try:
            payload = fetch_bytes(client, url, retries)
            if len(payload) > MAX_IMAGE_BYTES:
                raise ArticleImportError(f"图片超过 {MAX_IMAGE_BYTES} 字节上限")
            content_type = ""
            if payload.startswith(b"\x89PNG"):
                content_type = "image/png"
            elif payload.startswith(b"\xff\xd8\xff"):
                content_type = "image/jpeg"
            elif payload.startswith((b"GIF87a", b"GIF89a")):
                content_type = "image/gif"
            elif payload.startswith(b"RIFF") and payload[8:12] == b"WEBP":
                content_type = "image/webp"
            extension = infer_extension(url, content_type)
            filename = f"image-{index:03d}{extension}"
            target = image_dir / filename
            if overwrite or not target.exists():
                target.write_bytes(payload)
            record.update(
                status="archived_private",
                file=filename,
                bytes=len(payload),
                sha256=sha256_bytes(payload),
                content_type=content_type or "application/octet-stream",
            )
        except (ArticleImportError, httpx.HTTPError, OSError, ValueError) as exc:
            record.update(status="failed", error=str(exc))
        manifest.append(record)
    atomic_write_json(manifest_path, manifest)
    return manifest


def prepare_content(content: Tag, image_mode: str) -> tuple[str, list[str], int]:
    for comment in content.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for selector in ("script", "style", "noscript", ".qr_code_pc", ".reward_area"):
        for node in content.select(selector):
            node.decompose()
    for node in content.select("iframe, video"):
        placeholder = soup_new_tag(content, "p")
        placeholder.string = "[嵌入式音视频内容暂未归档]"
        node.replace_with(placeholder)

    urls: list[str] = []
    seen: set[str] = set()
    for image_number, img in enumerate(list(content.find_all("img")), start=1):
        url = image_url(img)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
        if image_mode == "remote" and url:
            img["src"] = url
            img.attrs.pop("data-src", None)
            img["alt"] = normalize_space(str(img.get("alt") or f"文章图片 {image_number}"))
        else:
            placeholder = soup_new_tag(content, "p")
            placeholder.string = f"[图像 {image_number:02d}：待版权审查，原图保存在私有归档]"
            img.replace_with(placeholder)

    raw_text = normalize_space(content.get_text(" ", strip=True))
    body_html = str(content)
    markdown = markdownify.markdownify(
        body_html,
        heading_style="ATX",
        bullets="-",
        strip=["span"],
    )
    markdown = markdown.replace("\u00a0", " ")
    markdown = re.sub(r"[ \t]+$", "", markdown, flags=re.MULTILINE)
    markdown = re.sub(r"\n{4,}", "\n\n\n", markdown).strip()
    return markdown, urls, len(re.sub(r"\s+", "", raw_text))


def soup_new_tag(node: Tag, name: str) -> Tag:
    root = node
    while getattr(root, "parent", None) is not None:
        root = root.parent  # type: ignore[assignment]
    if not isinstance(root, BeautifulSoup):
        raise ArticleImportError("无法定位 BeautifulSoup 文档根节点")
    return root.new_tag(name)


def yaml_document(metadata: dict, body: str) -> str:
    frontmatter = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
        default_flow_style=False,
    ).strip()
    return f"---\n{frontmatter}\n---\n\n{body.rstrip()}\n"


def build_article_markdown(metadata: dict, body_markdown: str) -> str:
    lines = [
        f"# {metadata['display_title']}",
        "",
        f"> 公众号：{metadata['account_name']}  ",
        f"> 发布时间：{metadata['published_at'][:10]}  ",
        f"> [查看微信原文]({metadata['source_url']})",
        "",
        '!!! note "归档说明"',
        "    本页由公开文章自动转换生成。图片暂不进入公开仓库，待逐项完成版权审查。",
        "",
        body_markdown,
    ]
    return yaml_document(metadata, "\n".join(lines))


def initial_state(inventory: list[dict], existing: list[dict]) -> dict[str, dict]:
    state = {str(row["id"]): row for row in existing}
    for row in inventory:
        state.setdefault(
            str(row["id"]),
            {
                "id": row["id"],
                "position": row["position"],
                "issue_no": row.get("issue_no"),
                "title": row["title"],
                "published_at": row["published_at"],
                "source_url": row["source_url"],
                "status": "discovered",
                "qa_status": "pending",
                "markdown_path": "",
                "text_chars": 0,
                "image_count": 0,
                "error": "",
                "updated_at": row.get("discovered_at", ""),
            },
        )
    return state


def select_inventory(rows: list[dict], args: argparse.Namespace) -> list[dict]:
    positions = {
        int(value)
        for token in (args.positions or "").split(",")
        for value in [token.strip()]
        if value
    }
    selected = [
        row
        for row in rows
        if (not positions or int(row["position"]) in positions)
        and int(row["position"]) >= args.start_position
        and (args.end_position <= 0 or int(row["position"]) <= args.end_position)
    ]
    selected.sort(key=lambda row: int(row["position"]))
    return selected[: args.limit] if args.limit > 0 else selected


def import_one(
    row: dict,
    *,
    client: httpx.Client,
    private_root: Path,
    public_root: Path,
    args: argparse.Namespace,
) -> dict:
    article_id = str(row["id"])
    year = str(row["published_at"])[:4] or "unknown"
    raw_path = private_root / "raw-html" / year / f"{article_id}.html"
    if raw_path.exists() and not args.overwrite:
        raw_bytes = raw_path.read_bytes()
        fetch_method = "private_cache"
        if not is_article_html(raw_bytes):
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            rejected_path = (
                private_root / "uncertain" / "verification-pages" / f"{article_id}-{stamp}.html"
            )
            rejected_path.parent.mkdir(parents=True, exist_ok=True)
            rejected_path.write_bytes(raw_bytes)
            raw_bytes, fetch_method = fetch_article_page(
                client,
                row,
                args.retries,
                args.sogou_fallback,
                args.curl_fallback,
                args.timeout,
            )
            raw_path.write_bytes(raw_bytes)
    else:
        raw_bytes, fetch_method = fetch_article_page(
            client,
            row,
            args.retries,
            args.sogou_fallback,
            args.curl_fallback,
            args.timeout,
        )
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw_bytes)

    raw_html = raw_bytes.decode("utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "html.parser")
    fetched_title, fetched_account, fetched_author, content = extract_page(soup)
    body_markdown, image_urls, text_chars = prepare_content(content, args.image_mode)
    if text_chars < args.min_text_chars:
        raise ArticleImportError(
            f"正文仅 {text_chars} 个非空白字符，低于阈值 {args.min_text_chars}"
        )

    image_manifest: list[dict] = []
    if not args.skip_image_backup:
        image_manifest = backup_images(
            client,
            image_urls,
            article_id,
            private_root,
            args.retries,
            args.overwrite,
        )

    inventory_title = normalize_space(str(row["title"]))
    title_match = inventory_title == fetched_title
    account_match = not fetched_account or fetched_account == row["account_name"]
    qa_status = "pass" if title_match and account_match else "review"
    relative_path = Path("docs") / "articles" / year / f"{int(row['position']):04d}-{article_id}.md"
    metadata = {
        "title": fetched_title,
        "display_title": row["display_title"],
        "date": str(row["published_at"])[:10],
        "published_at": row["published_at"],
        "account_name": row["account_name"],
        "author": fetched_author,
        "source_url": row["source_url"],
        "article_id": article_id,
        "position": int(row["position"]),
        "issue_no": row.get("issue_no"),
        "series": row.get("series") or "未分类",
        "tags": [row.get("series") or "未分类"],
        "content_rights": row.get("content_rights", "pending_owner_review"),
        "asset_rights": row.get("asset_rights", "pending_review"),
        "image_policy": args.image_mode,
        "image_count": len(image_urls),
        "text_chars": text_chars,
        "raw_sha256": sha256_bytes(raw_bytes),
        "fetch_method": fetch_method,
        "qa_status": qa_status,
        "imported_at": utc_now(),
    }
    atomic_write_text(public_root / relative_path, build_article_markdown(metadata, body_markdown))
    return {
        "id": article_id,
        "position": int(row["position"]),
        "issue_no": row.get("issue_no"),
        "title": fetched_title,
        "published_at": row["published_at"],
        "source_url": row["source_url"],
        "status": "imported",
        "qa_status": qa_status,
        "markdown_path": relative_path.as_posix(),
        "text_chars": text_chars,
        "image_count": len(image_urls),
        "archived_image_count": sum(
            1 for item in image_manifest if item.get("status") == "archived_private"
        ),
        "raw_sha256": metadata["raw_sha256"],
        "fetch_method": fetch_method,
        "title_match": title_match,
        "account_match": account_match,
        "error": "",
        "updated_at": metadata["imported_at"],
    }


def run(args: argparse.Namespace) -> int:
    inventory = jsonl_load(args.inventory.resolve())
    selected = select_inventory(inventory, args)
    private_root = args.private_root.resolve()
    public_root = args.public_root.resolve()
    public_state_path = public_root / "data" / "import-status.jsonl"
    private_state_path = private_root / "indexes" / "import-status.jsonl"
    existing = jsonl_load(private_state_path) if private_state_path.exists() else []
    state = initial_state(inventory, existing)
    imported = failed = skipped = 0

    headers = {
        "User-Agent": DESKTOP_UA,
        "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://mp.weixin.qq.com/",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=args.timeout) as client:
        for row in selected:
            article_id = str(row["id"])
            if state.get(article_id, {}).get("status") == "imported" and not args.overwrite:
                print(f"skip position={row['position']} id={article_id} reason=already_imported")
                skipped += 1
                continue
            try:
                result = import_one(
                    row,
                    client=client,
                    private_root=private_root,
                    public_root=public_root,
                    args=args,
                )
                state[article_id] = result
                imported += 1
                print(
                    f"ok position={row['position']} id={article_id} "
                    f"chars={result['text_chars']} images={result['image_count']} "
                    f"qa={result['qa_status']}"
                )
            except (ArticleImportError, httpx.HTTPError, OSError, ValueError) as exc:
                failed += 1
                state[article_id] = {
                    **state[article_id],
                    "status": "failed",
                    "qa_status": "review",
                    "error": str(exc),
                    "updated_at": utc_now(),
                }
                print(f"failed position={row['position']} id={article_id} error={exc}")
            ordered = sorted(state.values(), key=lambda item: (int(item["position"]), item["id"]))
            jsonl_dump(ordered, private_state_path)
            jsonl_dump(ordered, public_state_path)
            if args.delay > 0:
                time.sleep(args.delay)

    print(
        json.dumps(
            {"selected": len(selected), "imported": imported, "failed": failed, "skipped": skipped},
            ensure_ascii=False,
        )
    )
    return 1 if failed and args.fail_on_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import public WeChat articles into the knowledge base"
    )
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--positions", help="Comma-separated album positions")
    parser.add_argument("--start-position", type=int, default=1)
    parser.add_argument("--end-position", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--image-mode", choices=("placeholder", "remote"), default="placeholder")
    parser.add_argument(
        "--sogou-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Resolve a public Sogou WeChat result if the direct URL returns a verification page",
    )
    parser.add_argument(
        "--curl-fallback",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use system curl for the same public WeChat URL before trying Sogou",
    )
    parser.add_argument("--skip-image-backup", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--min-text-chars", type=int, default=100)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--fail-on-error", action="store_true")
    return parser


if __name__ == "__main__":
    raise SystemExit(run(build_parser().parse_args()))

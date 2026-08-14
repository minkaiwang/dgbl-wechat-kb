from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

WECHAT_UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/110.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.43"
)
CHINA_TZ = timezone(timedelta(hours=8))


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
            handle.write(text)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, value: object) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def format_timestamp(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    return datetime.fromtimestamp(int(value), tz=CHINA_TZ).isoformat(timespec="seconds")


def canonical_wechat_url(raw_url: str) -> str:
    value = html.unescape(raw_url).replace("\\x26amp;", "&").strip()
    parts = urlsplit(value)
    if parts.hostname != "mp.weixin.qq.com":
        return value
    # chksm is part of WeChat's public article validation. Removing it can
    # redirect otherwise valid album links to the public captcha page.
    keep_order = ("__biz", "mid", "idx", "sn", "chksm")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    selected = [(key, query[key]) for key in keep_order if query.get(key)]
    if not selected:
        return urlunsplit(("https", "mp.weixin.qq.com", parts.path, parts.query, ""))
    return urlunsplit(("https", "mp.weixin.qq.com", "/s", urlencode(selected), ""))


TITLE_RE = re.compile(r"^\[(.*?)(?:\s+(\d+))?\]\s*(.*)$")


def parse_title(title: str) -> tuple[str, int | None, str]:
    match = TITLE_RE.match(title.strip())
    if not match:
        return "未分类", None, title.strip()
    series = match.group(1).strip()
    issue = int(match.group(2)) if match.group(2) else None
    clean_title = match.group(3).strip() or title.strip()
    return series, issue, clean_title


def stable_article_id(msgid: str | int, itemidx: str | int) -> str:
    return f"wx-{int(msgid)}-{int(itemidx)}"


def jsonl_dump(rows: list[dict], path: Path) -> None:
    content = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    atomic_write_text(path, content)


def jsonl_load(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at {path}:{number}: {exc}") from exc
    return rows


def read_markdown_frontmatter(path: Path) -> tuple[dict, str]:
    """Return YAML frontmatter and body from a Markdown document."""
    import yaml

    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        raise ValueError(f"Unclosed YAML frontmatter: {path}")
    metadata = yaml.safe_load(text[4:boundary]) or {}
    if not isinstance(metadata, dict):
        raise TypeError(f"YAML frontmatter must be a mapping: {path}")
    return metadata, text[boundary + 5 :]

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml
from kb_common import atomic_write_text, read_markdown_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OLD_NOTE = "本页由公开文章自动转换生成。图片暂不进入公开仓库，待逐项完成版权审查。"
LICENSED_NOTE = (
    "本页正文由公众号所有者“靓点迷人”按 CC BY-NC 4.0 授权；图片未进入仓库，"
    "图像占位符对应素材保持原有权利状态。"
)
PLACEHOLDER_RE = re.compile(r"^\[图像 \d+：待版权审查，原图保存在私有归档\]$", re.MULTILINE)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
REMOTE_IMAGE_RE = re.compile(r"!\[[^]]*]\(https?://|<img\b|data:image/", re.IGNORECASE)


def load_manifest(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "account_name",
        "licensor_credit",
        "license",
        "license_url",
        "scope",
    }
    missing = sorted(required - value.keys())
    if missing:
        raise ValueError(f"license manifest is missing fields: {missing}")
    scope = value["scope"]
    if not isinstance(scope, dict):
        raise TypeError("license manifest scope must be an object")
    for field in ("position_min", "position_max", "article_count"):
        if field not in scope:
            raise ValueError(f"license manifest scope is missing {field}")
    return value


def markdown_document(metadata: dict, body: str) -> str:
    frontmatter = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        width=1000,
        default_flow_style=False,
    ).strip()
    return f"---\n{frontmatter}\n---\n\n{body.lstrip().rstrip()}\n"


def licensed_article(path: Path, manifest: dict) -> tuple[str, dict]:
    metadata, body = read_markdown_frontmatter(path)
    body = re.sub(
        r"^(> (?:公众号：|发布时间：)[^\r\n]+?) {2}$",
        r"\1<br>",
        body,
        flags=re.MULTILINE,
    )
    position = int(metadata.get("position", 0))
    scope = manifest["scope"]
    if not int(scope["position_min"]) <= position <= int(scope["position_max"]):
        raise ValueError(f"article position is outside the licensed scope: {path}")
    if metadata.get("account_name") != manifest["account_name"]:
        raise ValueError(f"account name does not match the license manifest: {path}")
    if metadata.get("author") != manifest["licensor_credit"]:
        raise ValueError(f"author does not match the licensor credit: {path}")
    if metadata.get("qa_status") != "pass":
        raise ValueError(f"article has not passed QA: {path}")
    if metadata.get("image_policy") != "placeholder":
        raise ValueError(f"article does not use the placeholder image policy: {path}")
    if metadata.get("asset_rights") != "pending_review":
        raise ValueError(f"unexpected asset-rights state: {path}")
    if REMOTE_IMAGE_RE.search(body):
        raise ValueError(f"article contains an embedded image: {path}")
    if EMAIL_RE.search(body):
        raise ValueError(f"article contains an email address: {path}")

    if OLD_NOTE in body:
        body = body.replace(OLD_NOTE, LICENSED_NOTE, 1)
    elif LICENSED_NOTE not in body:
        raise ValueError(f"article is missing the expected archive note: {path}")

    occurrence_count = len(PLACEHOLDER_RE.findall(body))
    unique_image_count = int(metadata.get("image_count", 0))
    if occurrence_count < unique_image_count:
        raise ValueError(
            f"image placeholders ({occurrence_count}) are fewer than unique images "
            f"({unique_image_count}): {path}"
        )

    metadata["content_rights"] = manifest["license"]
    metadata["content_license_url"] = manifest["license_url"]
    metadata["licensor"] = manifest["licensor_credit"]
    metadata["image_occurrence_count"] = occurrence_count
    return markdown_document(metadata, body), {
        "article_id": str(metadata["article_id"]),
        "position": position,
        "unique_image_count": unique_image_count,
        "image_occurrence_count": occurrence_count,
    }


def apply_license(root: Path, manifest_path: Path, *, write: bool) -> dict:
    manifest = load_manifest(manifest_path)
    article_paths = sorted((root / "docs" / "articles").rglob("*.md"))
    article_paths = [path for path in article_paths if path.name != "index.md"]
    expected_count = int(manifest["scope"]["article_count"])
    if len(article_paths) != expected_count:
        raise ValueError(f"found {len(article_paths)} article files; expected {expected_count}")

    changed = 0
    rows: list[dict] = []
    for path in article_paths:
        updated, row = licensed_article(path, manifest)
        current = path.read_text(encoding="utf-8")
        if current != updated:
            changed += 1
            if write:
                atomic_write_text(path, updated)
        rows.append(row)

    positions = sorted(row["position"] for row in rows)
    expected_positions = list(
        range(
            int(manifest["scope"]["position_min"]),
            int(manifest["scope"]["position_max"]) + 1,
        )
    )
    if positions != expected_positions:
        raise ValueError("article positions do not match the licensed consecutive range")
    return {
        "license": manifest["license"],
        "licensor": manifest["licensor_credit"],
        "articles": len(rows),
        "changed": changed,
        "write": write,
        "unique_image_count": sum(row["unique_image_count"] for row in rows),
        "image_occurrence_count": sum(row["image_occurrence_count"] for row in rows),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply an audited text license to article Markdown")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "content-license.json",
    )
    parser.add_argument("--write", action="store_true", help="write validated frontmatter and notes")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = apply_license(args.root.resolve(), args.manifest.resolve(), write=args.write)
    print(json.dumps(result, ensure_ascii=False, indent=2))

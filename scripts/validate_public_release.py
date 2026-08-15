from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml
from build_fulltext_dataset import (
    EXPECTED_LICENSE_URL,
    EXPECTED_LICENSOR,
    EXPECTED_TEXT_LICENSE,
    collect_fulltext,
)
from kb_common import jsonl_load

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ARTICLE_COUNT = 475
MAX_PUBLIC_FILE_BYTES = 20 * 1024 * 1024
EXPECTED_ACCOUNT_NAME = "数字游戏学习研究"
EXPECTED_RELEASE_VERSION = "0.2.0"

PUBLIC_METADATA_FIELDS = {
    "schema_version",
    "article_id",
    "position",
    "issue_no",
    "title",
    "display_title",
    "series",
    "author",
    "licensor",
    "published_at",
    "source_url",
    "content_rights",
    "content_license_url",
    "asset_rights",
}
REQUIRED_METADATA_FIELDS = {
    "schema_version",
    "article_id",
    "position",
    "title",
    "author",
    "licensor",
    "published_at",
    "source_url",
    "content_rights",
    "content_license_url",
    "asset_rights",
}
FORBIDDEN_EXACT_PATHS: set[str] = set()
FORBIDDEN_PATH_PREFIXES = (
    "docs/assets/images/pending/",
    "private-archive/",
)
REQUIRED_RELEASE_FILES = {
    ".github/workflows/ci.yml",
    "CHANGELOG.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "DATA-LICENSE.md",
    "LICENSE",
    "PUBLIC_SCOPE.md",
    "README.md",
    "RIGHTS.md",
    "SECURITY.md",
    "TEXT-LICENSE.md",
    "data/article-fulltext.schema.json",
    "data/article-metadata.jsonl",
    "data/article-metadata.schema.json",
    "data/articles.jsonl",
    "data/content-license.json",
    "data/import-status.jsonl",
    "docs/assets/readme-overview.svg",
    "docs/catalog.md",
    "docs/catalog-public.md",
    "docs/dataset.md",
    "docs/llms.txt",
    "reports/fulltext-redactions.csv",
    "reports/public-release-v0.2.0.md",
    "reports/readme-svg-v0.2.0.md",
    "reports/release-notes-v0.2.0.md",
    "reports/text-authorization-v0.2.0.md",
    "scripts/apply_text_license.py",
    "scripts/build_fulltext_dataset.py",
    "scripts/build_release_assets.py",
}


def run_git(root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=text,
    )
    return result.stdout


def candidate_files(root: Path) -> list[str]:
    output = run_git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({value for value in str(output).split("\0") if value})


def forbidden_paths(paths: list[str]) -> list[str]:
    blocked: list[str] = []
    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        if path in FORBIDDEN_EXACT_PATHS or path.startswith(FORBIDDEN_PATH_PREFIXES):
            blocked.append(path)
    return sorted(blocked)


def secret_patterns() -> dict[str, re.Pattern[str]]:
    return {
        "private key": re.compile("-----BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "GitHub token": re.compile(
            r"\b(?:gh" + r"[pousr]_[A-Za-z0-9]{20,}|github" + r"_pat_[A-Za-z0-9_]{20,})\b"
        ),
        "OpenAI-style key": re.compile(r"\bsk" + r"-[A-Za-z0-9_-]{20,}\b"),
        "AWS access key": re.compile(r"\bAK" + r"IA[0-9A-Z]{16}\b"),
        "Google API key": re.compile(r"\bAI" + r"za[0-9A-Za-z_-]{30,}\b"),
    }


def text_findings(path: str, text: str) -> list[str]:
    findings = [name for name, pattern in secret_patterns().items() if pattern.search(text)]
    if re.search(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\\/\s]+", text):
        findings.append("personal Windows user path")
    emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))
    personal_emails = sorted(
        email
        for email in emails
        if not email.lower().endswith("@users.noreply.github.com")
        and email.rsplit("@", 1)[-1].lower() not in {"example.com", "example.net", "example.org"}
    )
    if personal_emails:
        findings.append("email address: " + ", ".join(personal_emails))
    return [f"{path}: {finding}" for finding in findings]


def scan_candidate_files(root: Path, paths: list[str]) -> tuple[list[str], int]:
    findings: list[str] = []
    scanned_text_files = 0
    for relative in paths:
        path = root / relative
        if path.is_symlink():
            findings.append(f"{relative}: symbolic links are not allowed in the public release")
            continue
        size = path.stat().st_size
        if size > MAX_PUBLIC_FILE_BYTES:
            findings.append(f"{relative}: file is larger than 20 MiB ({size} bytes)")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        scanned_text_files += 1
        findings.extend(text_findings(relative, text))
    return findings, scanned_text_files


def validate_public_metadata(rows: list[dict], expected_count: int) -> list[str]:
    errors: list[str] = []
    if len(rows) != expected_count:
        errors.append(f"metadata count is {len(rows)}; expected {expected_count}")

    ids: list[str] = []
    urls: list[str] = []
    positions: list[int] = []
    for number, row in enumerate(rows, start=1):
        missing = sorted(REQUIRED_METADATA_FIELDS - row.keys())
        extra = sorted(row.keys() - PUBLIC_METADATA_FIELDS)
        if missing:
            errors.append(f"row {number}: missing fields {missing}")
        if extra:
            errors.append(f"row {number}: non-public fields {extra}")

        if row.get("schema_version") != 2:
            errors.append(f"row {number}: schema_version must be 2")

        article_id = str(row.get("article_id", ""))
        if not re.fullmatch(r"wx-\d+-\d+", article_id):
            errors.append(f"row {number}: invalid article_id {article_id!r}")
        ids.append(article_id)

        try:
            position = int(row.get("position"))
        except (TypeError, ValueError):
            errors.append(f"row {number}: invalid position {row.get('position')!r}")
        else:
            positions.append(position)

        url = str(row.get("source_url", ""))
        parts = urlsplit(url)
        query = parse_qs(parts.query)
        if parts.scheme != "https" or parts.netloc != "mp.weixin.qq.com" or parts.path != "/s":
            errors.append(f"row {number}: unexpected source URL {url!r}")
        if not all(query.get(key) for key in ("__biz", "mid", "idx", "sn")):
            errors.append(f"row {number}: source URL is missing a required WeChat field")
        urls.append(url)

        if row.get("author") != EXPECTED_LICENSOR:
            errors.append(f"row {number}: unexpected author value")
        if row.get("licensor") != EXPECTED_LICENSOR:
            errors.append(f"row {number}: unexpected licensor value")
        if row.get("content_rights") != EXPECTED_TEXT_LICENSE:
            errors.append(f"row {number}: unexpected content_rights value")
        if row.get("content_license_url") != EXPECTED_LICENSE_URL:
            errors.append(f"row {number}: unexpected content_license_url value")
        if row.get("asset_rights") != "pending_review":
            errors.append(f"row {number}: unexpected asset_rights value")

    expected_positions = list(range(1, expected_count + 1))
    if positions != expected_positions:
        errors.append("metadata positions are not the ordered consecutive range 1..expected_count")
    if len(ids) != len(set(ids)):
        errors.append("duplicate article_id values found")
    if len(urls) != len(set(urls)):
        errors.append("duplicate source_url values found")
    return errors


def validate_import_status(rows: list[dict], metadata_rows: list[dict]) -> list[str]:
    errors: list[str] = []
    if len(rows) != len(metadata_rows):
        errors.append(f"import status count is {len(rows)}; metadata count is {len(metadata_rows)}")
    status_ids = [str(row.get("id", "")) for row in rows]
    metadata_ids = [str(row.get("article_id", "")) for row in metadata_rows]
    if status_ids != metadata_ids:
        errors.append("import status IDs do not match metadata IDs in order")
    if any(row.get("status") != "imported" for row in rows):
        errors.append("one or more import status rows are not imported")
    return errors


def validate_catalog(text: str, expected_count: int) -> list[str]:
    errors: list[str] = []
    if text.count("[微信原文](") != expected_count:
        errors.append("public catalog link count does not match expected metadata count")
    if text.count("](articles/") != expected_count:
        errors.append("public catalog full-text link count does not match expected metadata count")
    for forbidden in ("<script", "javascript:"):
        if forbidden.lower() in text.lower():
            errors.append(f"public catalog contains forbidden content: {forbidden}")
    return errors


def validate_content_license(value: object, expected_count: int) -> list[str]:
    if not isinstance(value, dict):
        return ["content-license.json is not a JSON object"]
    errors: list[str] = []
    expected = {
        "schema_version": 1,
        "authorization_date": "2026-08-15",
        "account_name": EXPECTED_ACCOUNT_NAME,
        "licensor_credit": EXPECTED_LICENSOR,
        "license": EXPECTED_TEXT_LICENSE,
        "license_url": EXPECTED_LICENSE_URL,
        "future_articles_default": "pending_owner_review",
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            errors.append(f"content-license.json has unexpected {field}")
    scope = value.get("scope")
    if not isinstance(scope, dict):
        errors.append("content-license.json scope is not an object")
        return errors
    if scope.get("position_min") != 1 or scope.get("position_max") != expected_count:
        errors.append("content-license.json position range does not match the release")
    if scope.get("article_count") != expected_count:
        errors.append("content-license.json article count does not match the release")
    return errors


def validate_fulltext_articles(
    root: Path, metadata_rows: list[dict], expected_count: int, candidate_paths: list[str]
) -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    article_candidates = sorted(
        path
        for path in candidate_paths
        if path.startswith("docs/articles/") and path.endswith(".md")
    )
    if len(article_candidates) != expected_count:
        errors.append(
            f"candidate article count is {len(article_candidates)}; expected {expected_count}"
        )
    try:
        rows = collect_fulltext(root, expected_count)
    except (KeyError, TypeError, ValueError) as exc:
        return [*errors, f"full-text article validation failed: {exc}"], []

    fulltext_paths = sorted(str(row["markdown_path"]) for row in rows)
    if article_candidates != fulltext_paths:
        errors.append("candidate article paths do not match the validated full-text records")
    if len(metadata_rows) == len(rows):
        comparable_fields = (
            "article_id",
            "position",
            "title",
            "author",
            "licensor",
            "published_at",
            "source_url",
            "content_rights",
            "content_license_url",
            "asset_rights",
        )
        for number, (metadata, article) in enumerate(zip(metadata_rows, rows, strict=True), start=1):
            mismatched = [field for field in comparable_fields if metadata.get(field) != article.get(field)]
            if mismatched:
                errors.append(f"row {number}: metadata/full-text mismatch in {mismatched}")
    return errors, rows


def validate_derived_indexes(root: Path, article_rows: list[dict], expected_count: int) -> list[str]:
    errors: list[str] = []
    index_rows = jsonl_load(root / "data" / "articles.jsonl")
    if len(index_rows) != expected_count:
        errors.append(f"article index count is {len(index_rows)}; expected {expected_count}")
    if {str(row.get("article_id")) for row in index_rows} != {
        str(row.get("article_id")) for row in article_rows
    }:
        errors.append("article index IDs do not match full-text article IDs")

    catalog = (root / "docs" / "catalog.md").read_text(encoding="utf-8")
    if catalog.count("](articles/") != expected_count or catalog.count("[微信](") != expected_count:
        errors.append("article catalog does not contain one local and source link per article")

    llms = (root / "docs" / "llms.txt").read_text(encoding="utf-8")
    if llms.count("- 本地: docs/articles/") != expected_count:
        errors.append("llms index does not contain one local path per article")
    if llms.count("- 原文: https://mp.weixin.qq.com/s?") != expected_count:
        errors.append("llms index does not contain one source URL per article")
    return errors


def validate_citation(path: Path) -> list[str]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["CITATION.cff is not a YAML mapping"]
    for key in ("cff-version", "message", "title", "authors", "version"):
        if not value.get(key):
            errors.append(f"CITATION.cff is missing {key}")
    if value.get("cff-version") != "1.2.0":
        errors.append("CITATION.cff must use cff-version 1.2.0")
    if value.get("version") != EXPECTED_RELEASE_VERSION:
        errors.append(f"CITATION.cff version must be {EXPECTED_RELEASE_VERSION}")
    if value.get("license") != EXPECTED_TEXT_LICENSE:
        errors.append(f"CITATION.cff license must be {EXPECTED_TEXT_LICENSE}")
    authors = value.get("authors")
    if not isinstance(authors, list) or not any(
        isinstance(author, dict) and author.get("name") == EXPECTED_LICENSOR
        for author in authors
    ):
        errors.append(f"CITATION.cff must credit {EXPECTED_LICENSOR}")
    return errors


def validate_history(root: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    object_lines = str(run_git(root, "rev-list", "--objects", "--all")).splitlines()
    objects: list[tuple[str, str]] = []
    for line in object_lines:
        parts = line.split(" ", 1)
        if len(parts) == 2:
            objects.append((parts[0], parts[1].replace("\\", "/")))

    historical_paths = [path for _, path in objects]
    blocked = forbidden_paths(historical_paths)
    errors.extend(f"history contains forbidden path: {path}" for path in blocked)

    scanned_blobs = 0
    for oid, path in objects:
        if str(run_git(root, "cat-file", "-t", oid)).strip() != "blob":
            continue
        size = int(str(run_git(root, "cat-file", "-s", oid)).strip())
        if size > MAX_PUBLIC_FILE_BYTES:
            errors.append(f"history blob is larger than 20 MiB: {path} ({size} bytes)")
        payload = run_git(root, "cat-file", "-p", oid, text=False)
        try:
            text = bytes(payload).decode("utf-8")
        except UnicodeDecodeError:
            continue
        scanned_blobs += 1
        errors.extend(text_findings(f"history:{path}", text))

    log_emails = str(run_git(root, "log", "--all", "--format=%ae%n%ce")).splitlines()
    disallowed = sorted(
        {
            email
            for email in log_emails
            if email and not email.lower().endswith("@users.noreply.github.com")
        }
    )
    if disallowed:
        errors.append("Git history contains non-noreply email addresses: " + ", ".join(disallowed))
    return errors, scanned_blobs


def validate_release(root: Path, expected_count: int, check_history: bool) -> dict:
    paths = candidate_files(root)
    errors = [f"forbidden candidate path: {path}" for path in forbidden_paths(paths)]
    missing_files = sorted(REQUIRED_RELEASE_FILES - set(paths))
    errors.extend(f"required release file is missing: {path}" for path in missing_files)

    file_findings, scanned_text_files = scan_candidate_files(root, paths)
    errors.extend(file_findings)

    metadata_rows = jsonl_load(root / "data" / "article-metadata.jsonl")
    status_rows = jsonl_load(root / "data" / "import-status.jsonl")
    errors.extend(validate_public_metadata(metadata_rows, expected_count))
    errors.extend(validate_import_status(status_rows, metadata_rows))
    errors.extend(
        validate_catalog((root / "docs" / "catalog-public.md").read_text(encoding="utf-8"), expected_count)
    )
    license_value = json.loads((root / "data" / "content-license.json").read_text(encoding="utf-8"))
    errors.extend(validate_content_license(license_value, expected_count))
    article_errors, article_rows = validate_fulltext_articles(
        root, metadata_rows, expected_count, paths
    )
    errors.extend(article_errors)
    if article_rows:
        errors.extend(validate_derived_indexes(root, article_rows, expected_count))
    errors.extend(validate_citation(root / "CITATION.cff"))

    history_blobs = 0
    if check_history:
        history_errors, history_blobs = validate_history(root)
        errors.extend(history_errors)

    return {
        "status": "pass" if not errors else "fail",
        "candidate_files": len(paths),
        "metadata_rows": len(metadata_rows),
        "import_status_rows": len(status_rows),
        "scanned_text_files": scanned_text_files,
        "history_blobs_scanned": history_blobs,
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the public full-text release boundary")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ARTICLE_COUNT)
    parser.add_argument("--history", action="store_true", help="scan every reachable Git blob")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = validate_release(args.root.resolve(), args.expected_count, args.history)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "pass" else 1)

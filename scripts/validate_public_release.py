from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml
from kb_common import jsonl_load

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ARTICLE_COUNT = 475
MAX_PUBLIC_FILE_BYTES = 20 * 1024 * 1024

PUBLIC_METADATA_FIELDS = {
    "schema_version",
    "article_id",
    "position",
    "issue_no",
    "title",
    "display_title",
    "series",
    "author",
    "published_at",
    "source_url",
    "content_rights",
    "asset_rights",
}
REQUIRED_METADATA_FIELDS = {
    "schema_version",
    "article_id",
    "position",
    "title",
    "published_at",
    "source_url",
    "content_rights",
    "asset_rights",
}
FORBIDDEN_EXACT_PATHS = {
    "data/articles.jsonl",
    "docs/catalog.md",
    "docs/llms.txt",
}
FORBIDDEN_PATH_PREFIXES = (
    "docs/articles/",
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
    "data/article-metadata.jsonl",
    "data/article-metadata.schema.json",
    "data/import-status.jsonl",
    "docs/assets/readme-overview.svg",
    "docs/catalog-public.md",
    "docs/dataset.md",
    "reports/public-release-v0.1.1.md",
    "reports/release-notes-v0.1.1.md",
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
        email for email in emails if not email.lower().endswith("@users.noreply.github.com")
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

        if row.get("content_rights") != "pending_owner_review":
            errors.append(f"row {number}: unexpected content_rights value")
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
    for forbidden in ("docs/articles/", "data/articles.jsonl", "<script", "javascript:"):
        if forbidden.lower() in text.lower():
            errors.append(f"public catalog contains forbidden content: {forbidden}")
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
    parser = argparse.ArgumentParser(description="Validate the public metadata-only release boundary")
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--expected-count", type=int, default=EXPECTED_ARTICLE_COUNT)
    parser.add_argument("--history", action="store_true", help="scan every reachable Git blob")
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    result = validate_release(args.root.resolve(), args.expected_count, args.history)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "pass" else 1)

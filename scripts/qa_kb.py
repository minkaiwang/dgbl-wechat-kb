from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from build_index import collect_articles
from kb_common import atomic_write_json, atomic_write_text, jsonl_load

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_SCREENSHOT_ALBUM_COUNT = 474
PROFILE_SCREENSHOT_LABEL = "用户提供的主页截图（最新可见编号 482）"


def write_csv(rows: list[dict], path: Path) -> None:
    fields = list(rows[0].keys()) if rows else ["id", "position", "status", "error"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    atomic_write_text(path, buffer.getvalue())


def duplicates(values: list[str]) -> list[str]:
    counts = Counter(value for value in values if value)
    return sorted(value for value, count in counts.items() if count > 1)


def issue_gaps(inventory: list[dict]) -> tuple[int, list[int]]:
    issues = sorted({int(row["issue_no"]) for row in inventory if row.get("issue_no") is not None})
    if not issues:
        return 0, []
    maximum = max(issues)
    return maximum, sorted(set(range(1, maximum + 1)) - set(issues))


def duplicate_issue_numbers(inventory: list[dict]) -> list[int]:
    counts = Counter(int(row["issue_no"]) for row in inventory if row.get("issue_no") is not None)
    return sorted(issue for issue, count in counts.items() if count > 1)


def profile_reconciliation(
    *,
    profile_original_count: int,
    album_count_at_profile_snapshot: int,
    current_album_count: int,
    profile_snapshot_label: str,
) -> dict:
    if profile_original_count < album_count_at_profile_snapshot:
        raise ValueError("profile count cannot be smaller than the concurrent album count")
    if current_album_count < album_count_at_profile_snapshot:
        raise ValueError("current album count cannot be smaller than the profile-snapshot baseline")
    return {
        "expected_original_count_from_profile_screenshot": profile_original_count,
        "profile_snapshot_label": profile_snapshot_label,
        "album_count_at_profile_snapshot": album_count_at_profile_snapshot,
        "profile_to_album_gap": profile_original_count - album_count_at_profile_snapshot,
        "album_inventory_count": current_album_count,
        "album_items_added_since_profile_snapshot": (
            current_album_count - album_count_at_profile_snapshot
        ),
        "current_profile_count_reverified": False,
    }


def consecutive_ranges(values: list[int]) -> list[tuple[int, int]]:
    if not values:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = values[0]
    for value in values[1:]:
        if value != previous + 1:
            ranges.append((start, previous))
            start = value
        previous = value
    ranges.append((start, previous))
    return ranges


def published_datetime(row: dict | None) -> datetime | None:
    if not row or not row.get("published_at"):
        return None
    try:
        return datetime.fromisoformat(str(row["published_at"]))
    except ValueError:
        return None


def classify_issue_gaps(inventory: list[dict], gaps: list[int]) -> list[dict]:
    numbered = sorted(
        (row for row in inventory if row.get("issue_no") is not None),
        key=lambda row: int(row["issue_no"]),
    )
    classifications: list[dict] = []
    for start, end in consecutive_ranges(gaps):
        before = next(
            (row for row in reversed(numbered) if int(row["issue_no"]) < start),
            None,
        )
        after = next((row for row in numbered if int(row["issue_no"]) > end), None)
        before_dt = published_datetime(before)
        after_dt = published_datetime(after)
        elapsed_hours = None
        if before_dt and after_dt:
            elapsed_hours = round((after_dt - before_dt).total_seconds() / 3600, 2)
        positions_are_consecutive = bool(
            before
            and after
            and int(after["position"]) == int(before["position"]) + 1
        )
        probable_jump = bool(
            end > start
            and positions_are_consecutive
            and elapsed_hours is not None
            and 0 <= elapsed_hours <= 48
        )
        classifications.append(
            {
                "start": start,
                "end": end,
                "count": end - start + 1,
                "preceding_issue": int(before["issue_no"]) if before else None,
                "following_issue": int(after["issue_no"]) if after else None,
                "preceding_position": int(before["position"]) if before else None,
                "following_position": int(after["position"]) if after else None,
                "elapsed_hours": elapsed_hours,
                "classification": (
                    "probable_numbering_jump" if probable_jump else "unresolved_number_gap"
                ),
            }
        )
    return classifications


def run(args: argparse.Namespace) -> dict:
    root = args.public_root.resolve()
    inventory = jsonl_load(args.inventory.resolve())
    state_path = root / "data" / "import-status.jsonl"
    state = jsonl_load(state_path) if state_path.exists() else []
    articles = collect_articles(root)
    states = Counter(str(row.get("status", "unknown")) for row in state)
    maximum_issue, gaps = issue_gaps(inventory)
    gap_classifications = classify_issue_gaps(inventory, gaps)
    probable_jumps = [
        row for row in gap_classifications if row["classification"] == "probable_numbering_jump"
    ]
    unresolved_numbered_issues = [
        issue
        for row in gap_classifications
        if row["classification"] == "unresolved_number_gap"
        for issue in range(row["start"], row["end"] + 1)
    ]
    duplicate_issues = duplicate_issue_numbers(inventory)
    unnumbered = [str(row["id"]) for row in inventory if row.get("issue_no") is None]
    profile = profile_reconciliation(
        profile_original_count=args.expected_original_count,
        album_count_at_profile_snapshot=args.album_count_at_profile_snapshot,
        current_album_count=len(inventory),
        profile_snapshot_label=args.profile_snapshot_label,
    )
    pending = [
        {
            "id": row["id"],
            "position": row["position"],
            "status": row.get("status", "unknown"),
            "error": row.get("error", ""),
        }
        for row in state
        if row.get("status") != "imported"
    ]
    markdown_ids = [str(row["article_id"]) for row in articles]
    markdown_sources = [str(row["source_url"]) for row in articles]
    remote_images: list[str] = []
    dangerous_markup: list[str] = []
    for row in articles:
        text = (root / row["markdown_path"]).read_text(encoding="utf-8")
        if re.search(r"!\[[^]]*]\(https?://", text):
            remote_images.append(row["markdown_path"])
        if re.search(
            r"<script\b|javascript:|\bon(?:error|load)\s*=|<iframe\b", text, re.IGNORECASE
        ):
            dangerous_markup.append(row["markdown_path"])

    inventory_ids = {str(row["id"]) for row in inventory}
    state_ids = {str(row["id"]) for row in state}

    summary = {
        **profile,
        "maximum_numbered_issue": maximum_issue,
        "numbered_issue_gaps": gaps,
        "numbered_issue_gap_count": len(gaps),
        "issue_gap_classifications": gap_classifications,
        "probable_numbering_jump_ranges": probable_jumps,
        "unresolved_numbered_issues": unresolved_numbered_issues,
        "unresolved_numbered_issue_count": len(unresolved_numbered_issues),
        "duplicate_numbered_issues": duplicate_issues,
        "unnumbered_album_items": unnumbered,
        "import_status_counts": dict(sorted(states.items())),
        "markdown_article_count": len(articles),
        "duplicate_markdown_ids": duplicates(markdown_ids),
        "duplicate_source_urls": duplicates(markdown_sources),
        "remote_image_markdown_files": remote_images,
        "dangerous_markup_files": dangerous_markup,
        "inventory_without_state": sorted(inventory_ids - state_ids),
        "state_without_inventory": sorted(state_ids - inventory_ids),
        "imported_state_to_markdown_difference": states.get("imported", 0) - len(articles),
        "qa_review_count": sum(1 for row in articles if row.get("qa_status") != "pass"),
        "content_rights_pending_count": sum(
            1 for row in articles if row.get("content_rights") != "cleared"
        ),
        "asset_rights_pending_count": sum(
            1 for row in articles if row.get("asset_rights") != "cleared"
        ),
    }
    atomic_write_json(root / "reports" / "qa-summary.json", summary)
    write_csv(pending, root / "reports" / "pending-imports.csv")
    write_csv(
        [
            {
                "article_id": row["article_id"],
                "markdown_path": row["markdown_path"],
                "image_count": row["image_count"],
                "asset_rights": row["asset_rights"],
                "review_note": "逐图核对来源、许可与再分发条件",
            }
            for row in articles
        ],
        root / "reports" / "asset-rights.csv",
    )
    write_csv(
        [
            {
                "article_id": row["article_id"],
                "markdown_path": row["markdown_path"],
                "content_rights": row["content_rights"],
                "review_note": "确认作者构成与公开许可后再发布全文",
            }
            for row in articles
        ],
        root / "reports" / "content-rights.csv",
    )

    status_lines = [
        "# 知识库质量审计",
        "",
        f"- {args.profile_snapshot_label}显示原创内容：**{args.expected_original_count}** 篇。",
        (
            f"- 同期公开合集基线：**{args.album_count_at_profile_snapshot}** 篇；历史差额："
            f"**{profile['profile_to_album_gap']}** 篇。"
        ),
        (
            f"- 当前公开合集接口发现：**{len(inventory)}** 篇，位置连续 1–{len(inventory)}；"
            f"较截图同期新增 **{profile['album_items_added_since_profile_snapshot']}** 篇。"
        ),
        "- 主页原创数尚未在新增文章发布后重新截图，因此不计算异步的“当前主页数减当前合集数”。",
        f"- 合集最大编号：**{maximum_issue}**；编号序列缺口 **{len(gaps)}** 个："
        + ("、".join(map(str, gaps)) if gaps else "无"),
        "- 高度疑似一次性跳号的范围："
        + (
            "；".join(
                f"{row['start']}–{row['end']}（相邻合集位置仅相隔 {row['elapsed_hours']} 小时）"
                for row in probable_jumps
            )
            if probable_jumps
            else "无"
        ),
        f"- 仍需后台或人工清单核对的单个编号：**{len(unresolved_numbered_issues)}** 个："
        + ("、".join(map(str, unresolved_numbered_issues)) if unresolved_numbered_issues else "无"),
        f"- 重复编号：**{len(duplicate_issues)}** 个："
        + ("、".join(map(str, duplicate_issues)) if duplicate_issues else "无"),
        f"- 未识别编号的合集条目：**{len(unnumbered)}** 篇。",
        f"- 已生成 Markdown：**{len(articles)}** 篇。",
        f"- 导入状态：`{json.dumps(dict(sorted(states.items())), ensure_ascii=False)}`。",
        f"- 需人工复核的已导入文章：**{summary['qa_review_count']}** 篇。",
        f"- 公开 Markdown 中的远程图片链接：**{len(remote_images)}** 个文件。",
        f"- 危险内联标记命中：**{len(dangerous_markup)}** 个文件。",
        "",
        "## 结论",
        "",
        (
            "主页总数、合集条目数和编号序列属于三个不同口径。356–364 更可能是一次编号跳号，"
            f"不能算作九篇缺文；截图同期的 {profile['profile_to_album_gap']} 篇差额也不能与编号缺口"
            f"直接对应。当前可以确认 {len(inventory)} 篇合集文章；新增文章不会自动解释历史差额，"
            "账号全量完整性仍需公众号后台导出或人工清单核对。"
        ),
        "",
        "文字与图片的公开许可仍待权利人确认。当前仓库适合本地构建和技术评审，不应直接把文章正文套用代码 MIT 许可证后公开。",
    ]
    atomic_write_text(root / "reports" / "qa-summary.md", "\n".join(status_lines) + "\n")
    print(json.dumps(summary, ensure_ascii=False))
    has_hard_error = bool(
        pending
        or summary["duplicate_markdown_ids"]
        or summary["duplicate_source_urls"]
        or remote_images
        or dangerous_markup
        or summary["inventory_without_state"]
        or summary["state_without_inventory"]
        or summary["imported_state_to_markdown_difference"]
    )
    return {**summary, "strict_pass": not has_hard_error}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit knowledge-base completeness and safety")
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--expected-original-count", type=int, default=486)
    parser.add_argument(
        "--album-count-at-profile-snapshot",
        type=int,
        default=PROFILE_SCREENSHOT_ALBUM_COUNT,
        help="Album count observed concurrently with the profile screenshot",
    )
    parser.add_argument(
        "--profile-snapshot-label",
        default=PROFILE_SCREENSHOT_LABEL,
        help="Human-readable provenance label for the profile count",
    )
    parser.add_argument("--strict", action="store_true")
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    result = run(parsed)
    raise SystemExit(1 if parsed.strict and not result["strict_pass"] else 0)

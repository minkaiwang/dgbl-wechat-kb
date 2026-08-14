from __future__ import annotations

import pytest
from qa_kb import classify_issue_gaps, profile_reconciliation


def test_classify_multi_issue_jump_separately_from_single_gaps() -> None:
    inventory = [
        {"issue_no": 2, "position": 2, "published_at": "2024-07-12T10:04:43+08:00"},
        {"issue_no": 4, "position": 3, "published_at": "2024-07-18T14:48:14+08:00"},
        {"issue_no": 355, "position": 355, "published_at": "2026-02-17T11:40:22+08:00"},
        {"issue_no": 365, "position": 356, "published_at": "2026-02-18T09:31:52+08:00"},
    ]

    result = classify_issue_gaps(inventory, [3, *range(356, 365)])

    assert result[0]["classification"] == "unresolved_number_gap"
    assert result[0]["start"] == result[0]["end"] == 3
    assert result[1]["classification"] == "probable_numbering_jump"
    assert result[1]["start"] == 356
    assert result[1]["end"] == 364
    assert result[1]["preceding_position"] == 355
    assert result[1]["following_position"] == 356


def test_profile_reconciliation_keeps_snapshot_gap_separate_from_new_album_items() -> None:
    result = profile_reconciliation(
        profile_original_count=486,
        album_count_at_profile_snapshot=474,
        current_album_count=475,
        profile_snapshot_label="screenshot before issue 483",
    )

    assert result["profile_to_album_gap"] == 12
    assert result["album_items_added_since_profile_snapshot"] == 1
    assert result["current_profile_count_reverified"] is False


def test_profile_reconciliation_rejects_inconsistent_baselines() -> None:
    with pytest.raises(ValueError, match="concurrent album count"):
        profile_reconciliation(
            profile_original_count=473,
            album_count_at_profile_snapshot=474,
            current_album_count=475,
            profile_snapshot_label="invalid",
        )

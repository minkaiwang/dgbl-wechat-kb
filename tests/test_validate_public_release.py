from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from kb_common import jsonl_load
from validate_public_release import (
    EXPECTED_ARTICLE_COUNT,
    validate_catalog,
    validate_content_license,
    validate_public_metadata,
)

ROOT = Path(__file__).resolve().parents[1]


def current_metadata() -> list[dict]:
    return jsonl_load(ROOT / "data" / "article-metadata.jsonl")


def test_current_public_metadata_passes_release_schema() -> None:
    assert validate_public_metadata(current_metadata(), EXPECTED_ARTICLE_COUNT) == []


def test_body_field_is_rejected() -> None:
    rows = current_metadata()
    rows[0] = {**rows[0], "body": "should remain private"}
    errors = validate_public_metadata(rows, EXPECTED_ARTICLE_COUNT)
    assert any("non-public fields" in error and "body" in error for error in errors)


def test_nonconsecutive_positions_are_rejected() -> None:
    rows = deepcopy(current_metadata())
    rows[1]["position"] = 9
    errors = validate_public_metadata(rows, EXPECTED_ARTICLE_COUNT)
    assert any("ordered consecutive range" in error for error in errors)


def test_wrong_text_license_is_rejected() -> None:
    rows = deepcopy(current_metadata())
    rows[0]["content_rights"] = "pending_owner_review"
    errors = validate_public_metadata(rows, EXPECTED_ARTICLE_COUNT)
    assert any("unexpected content_rights" in error for error in errors)


def test_current_public_catalog_has_one_link_per_row() -> None:
    catalog = (ROOT / "docs" / "catalog-public.md").read_text(encoding="utf-8")
    assert validate_catalog(catalog, EXPECTED_ARTICLE_COUNT) == []


def test_current_content_license_matches_release_scope() -> None:
    import json

    value = json.loads((ROOT / "data" / "content-license.json").read_text(encoding="utf-8"))
    assert validate_content_license(value, EXPECTED_ARTICLE_COUNT) == []

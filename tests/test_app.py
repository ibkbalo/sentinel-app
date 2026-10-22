"""Automated tests for Sentinel App using Flask's built-in test client."""

import re

import pytest

from app import (
    CATEGORIES,
    SEVERITIES,
    STATUSES,
    app,
    build_summary,
    normalize_work_item_fields,
    validate_work_item,
)
from test_fixtures import EXPECTED_SYNTHETIC_SUMMARY, SYNTHETIC_WORK_ITEMS
from work_item_store import WorkItemStore


def valid_example_item():
    return {
        "id": "SWI-9999",
        "title": "Example remediation task",
        "category": CATEGORIES[0],
        "severity": SEVERITIES[0],
        "status": STATUSES[0],
        "owner": "Example Operator",
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask client backed by an empty temporary SQLite database."""
    monkeypatch.setenv("SENTINEL_APP_DB_PATH", str(tmp_path / "empty.db"))
    monkeypatch.delenv("SENTINEL_APP_DEMO_MODE", raising=False)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.fixture
def seeded_client(tmp_path, monkeypatch):
    """Flask client with synthetic work items inserted into a temp database."""
    db_path = tmp_path / "seeded.db"
    monkeypatch.setenv("SENTINEL_APP_DB_PATH", str(db_path))
    monkeypatch.delenv("SENTINEL_APP_DEMO_MODE", raising=False)
    store = WorkItemStore(db_path)
    store.initialize_schema()
    for item in SYNTHETIC_WORK_ITEMS:
        store.insert(item)
    store.close()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def card_value(html, label):
    """Return the number shown on the dashboard card with the given label."""
    match = re.search(
        rf'<div class="card-label">{re.escape(label)}</div>\s*'
        r'<div class="card-value">(\d+)</div>',
        html,
    )
    assert match, f"Dashboard card '{label}' not found"
    return int(match.group(1))


def test_dashboard_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_dashboard_contains_sentinel_stacks(client):
    html = client.get("/").get_data(as_text=True)
    assert "Sentinel Stacks" in html
    assert "Sentinel Stacks — Security Work Management" in html


def test_work_items_returns_200(client):
    response = client.get("/work-items")
    assert response.status_code == 200


def test_work_items_page_displays_seeded_items(seeded_client):
    html = seeded_client.get("/work-items").get_data(as_text=True)
    assert len(SYNTHETIC_WORK_ITEMS) > 0
    for item in SYNTHETIC_WORK_ITEMS:
        assert item["id"] in html
        assert item["title"] in html
        assert item["owner"] in html
    assert "loaded from the application database" in html


def test_work_items_page_displays_known_synthetic_item(seeded_client):
    html = seeded_client.get("/work-items").get_data(as_text=True)
    assert "SWI-9001" in html
    assert "Test: patch critical service dependency" in html
    assert "Vulnerability Remediation" in html


def test_empty_database_work_items_page(client):
    html = client.get("/work-items").get_data(as_text=True)
    assert "No work items are stored in the database yet" in html
    assert "SWI-9001" not in html
    assert "Demonstration mode" not in html


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_json(client):
    response = client.get("/health")
    assert response.is_json
    data = response.get_json()
    assert data["service"] == "sentinel-app"
    assert data["status"] == "healthy"


def test_build_summary_matches_synthetic_data():
    assert build_summary(SYNTHETIC_WORK_ITEMS) == EXPECTED_SYNTHETIC_SUMMARY


def test_dashboard_summary_counts_match_seeded_data(seeded_client):
    html = seeded_client.get("/").get_data(as_text=True)
    assert card_value(html, "Open Work Items") == EXPECTED_SYNTHETIC_SUMMARY["open"]
    assert card_value(html, "Critical Findings") == EXPECTED_SYNTHETIC_SUMMARY["critical"]
    assert (
        card_value(html, "Changes Awaiting Approval")
        == EXPECTED_SYNTHETIC_SUMMARY["awaiting_approval"]
    )
    assert card_value(html, "Completed Work") == EXPECTED_SYNTHETIC_SUMMARY["completed"]


def test_synthetic_work_items_validate_successfully():
    for item in SYNTHETIC_WORK_ITEMS:
        assert validate_work_item(item) == []


def test_synthetic_work_item_ids_are_unique():
    ids = [item["id"] for item in SYNTHETIC_WORK_ITEMS]
    assert len(ids) == len(set(ids))


def test_valid_example_item_is_accepted():
    assert validate_work_item(valid_example_item()) == []


def test_normalize_strips_whitespace_preserves_case():
    raw = {
        "id": "  SWI-9999  ",
        "title": "  Example remediation task  ",
        "category": "  Vulnerability Remediation  ",
        "severity": "  Critical  ",
        "status": "  Open  ",
        "owner": "  Example Operator  ",
    }
    normalized = normalize_work_item_fields(raw)
    assert normalized["id"] == "SWI-9999"
    assert normalized["title"] == "Example remediation task"
    assert normalized["category"] == "Vulnerability Remediation"
    assert normalized["severity"] == "Critical"
    assert normalized["status"] == "Open"
    assert normalized["owner"] == "Example Operator"
    assert validate_work_item(normalized) == []


def test_normalize_does_not_mutate_original():
    raw = {
        "id": "  SWI-9999  ",
        "title": "  Example  ",
        "category": CATEGORIES[0],
        "severity": SEVERITIES[0],
        "status": STATUSES[0],
        "owner": "  Operator  ",
    }
    original = dict(raw)
    normalize_work_item_fields(raw)
    assert raw == original


def test_validate_does_not_mutate_original():
    raw = {
        "id": "  SWI-9999  ",
        "title": "  Example  ",
        "category": f"  {CATEGORIES[0]}  ",
        "severity": f"  {SEVERITIES[0]}  ",
        "status": f"  {STATUSES[0]}  ",
        "owner": "  Operator  ",
    }
    original = dict(raw)
    assert validate_work_item(raw) == []
    assert raw == original


def test_missing_required_fields():
    errors = validate_work_item({})
    assert "Missing required field: id" in errors
    assert "Missing required field: title" in errors
    assert "Missing required field: owner" in errors
    assert "Missing required field: category" in errors
    assert "Missing required field: severity" in errors
    assert "Missing required field: status" in errors


def test_empty_and_whitespace_only_title():
    item = valid_example_item()
    item["title"] = ""
    assert any("title" in error for error in validate_work_item(item))

    item["title"] = "   "
    assert any("title" in error for error in validate_work_item(item))


def test_empty_and_whitespace_only_owner():
    item = valid_example_item()
    item["owner"] = ""
    assert any("owner" in error for error in validate_work_item(item))

    item["owner"] = "   "
    assert any("owner" in error for error in validate_work_item(item))


def test_invalid_category():
    item = valid_example_item()
    item["category"] = "Not A Real Category"
    errors = validate_work_item(item)
    assert any("category" in error for error in errors)


def test_invalid_severity():
    item = valid_example_item()
    item["severity"] = "Extreme"
    errors = validate_work_item(item)
    assert any("severity" in error for error in errors)


def test_invalid_status():
    item = valid_example_item()
    item["status"] = "Blocked"
    errors = validate_work_item(item)
    assert any("status" in error for error in errors)


def test_invalid_id_format():
    item = valid_example_item()
    item["id"] = "ITEM-1"
    errors = validate_work_item(item)
    assert any("id" in error for error in errors)

    item["id"] = "SWI-"
    assert any("id" in error for error in validate_work_item(item))


def test_duplicate_id_rejected_when_existing_ids_supplied():
    item = valid_example_item()
    item["id"] = "SWI-9001"
    errors = validate_work_item(item, existing_ids={"SWI-9001", "SWI-9002"})
    assert any("Duplicate" in error for error in errors)


def test_unexpected_non_string_field_values():
    item = valid_example_item()
    item["title"] = 123
    item["owner"] = None
    item["category"] = ["Vulnerability Remediation"]
    item["severity"] = 1
    item["status"] = {"name": "Open"}
    item["id"] = 1001
    errors = validate_work_item(item)
    assert any("title must be a string" in error for error in errors)
    assert any("owner must be a string" in error for error in errors)
    assert any("category must be a string" in error for error in errors)
    assert any("severity must be a string" in error for error in errors)
    assert any("status must be a string" in error for error in errors)
    assert any("id must be a string" in error for error in errors)


def test_non_dict_work_item_returns_error():
    assert validate_work_item("not-a-dict") == ["Work item must be a dictionary"]


def test_require_id_false_skips_id_checks():
    item = valid_example_item()
    del item["id"]
    assert validate_work_item(item, require_id=False) == []


def test_build_summary_unchanged_after_validation_helpers():
    assert build_summary(SYNTHETIC_WORK_ITEMS) == EXPECTED_SYNTHETIC_SUMMARY
    for item in SYNTHETIC_WORK_ITEMS:
        assert validate_work_item(item) == []
    assert build_summary(SYNTHETIC_WORK_ITEMS) == EXPECTED_SYNTHETIC_SUMMARY

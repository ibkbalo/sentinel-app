"""Flask + SQLite read-path integration tests."""

import re

import pytest

from app import CATEGORIES, SEVERITIES, STATUSES, app, build_summary
from work_item_store import WorkItemStore


def card_value(html, label):
    match = re.search(
        rf'<div class="card-label">{re.escape(label)}</div>\s*'
        r'<div class="card-value">(\d+)</div>',
        html,
    )
    assert match, f"Dashboard card '{label}' not found"
    return int(match.group(1))


@pytest.fixture
def sqlite_client(tmp_path, monkeypatch):
    """Flask test client using a temporary SQLite database."""
    db_path = tmp_path / "integration.db"
    monkeypatch.setenv("SENTINEL_APP_DB_PATH", str(db_path))
    monkeypatch.delenv("SENTINEL_APP_DEMO_MODE", raising=False)
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client, db_path


def test_import_app_and_store_without_circular_dependency():
    import app as app_module
    import work_item_store as store_module
    import work_item_validation as validation_module

    assert app_module.app is not None
    assert store_module.WorkItemStore is not None
    assert validation_module.validate_work_item is not None
    assert not hasattr(app_module, "WORK_ITEMS")
    assert not hasattr(app_module, "demo_mode_enabled")
    assert "app" not in store_module.__dict__ or store_module.__dict__.get("app") is None


def test_empty_database_shows_professional_empty_state(sqlite_client):
    client, db_path = sqlite_client

    work_html = client.get("/work-items").get_data(as_text=True)
    assert client.get("/work-items").status_code == 200
    assert "No work items are stored in the database yet" in work_html
    assert "Demonstration mode" not in work_html
    assert "SWI-9001" not in work_html

    dash_html = client.get("/").get_data(as_text=True)
    assert card_value(dash_html, "Open Work Items") == 0
    assert card_value(dash_html, "Critical Findings") == 0
    assert card_value(dash_html, "Changes Awaiting Approval") == 0
    assert card_value(dash_html, "Completed Work") == 0

    store = WorkItemStore(db_path)
    store.initialize_schema()
    assert store.list_all() == []
    store.close()


def test_browsing_empty_app_does_not_insert_records(sqlite_client):
    client, db_path = sqlite_client
    assert client.get("/").status_code == 200
    assert client.get("/work-items").status_code == 200

    store = WorkItemStore(db_path)
    store.initialize_schema()
    assert store.list_all() == []
    store.close()


def test_inserted_sqlite_rows_appear_on_both_pages(sqlite_client):
    client, db_path = sqlite_client
    store = WorkItemStore(db_path)
    store.initialize_schema()
    store.insert(
        {
            "id": "SWI-5001",
            "title": "Rotate expired TLS certificate",
            "category": CATEGORIES[0],
            "severity": SEVERITIES[0],
            "status": STATUSES[0],
            "owner": "Lab Operator",
        }
    )
    store.insert(
        {
            "id": "SWI-5002",
            "title": "Review IAM policy drift",
            "category": CATEGORIES[1],
            "severity": SEVERITIES[1],
            "status": STATUSES[2],
            "owner": "Lab Operator",
        }
    )
    store.close()

    work_html = client.get("/work-items").get_data(as_text=True)
    assert "SWI-5001" in work_html
    assert "Rotate expired TLS certificate" in work_html
    assert "SWI-5002" in work_html
    assert "Review IAM policy drift" in work_html
    assert "loaded from the application database" in work_html

    dash_html = client.get("/").get_data(as_text=True)
    assert card_value(dash_html, "Open Work Items") == 2
    assert card_value(dash_html, "Critical Findings") == 1
    assert card_value(dash_html, "Changes Awaiting Approval") == 1
    assert card_value(dash_html, "Completed Work") == 0


def test_dashboard_summary_reflects_database_records(sqlite_client):
    client, db_path = sqlite_client
    store = WorkItemStore(db_path)
    store.initialize_schema()
    items = [
        {
            "id": "SWI-5101",
            "title": "Completed control review",
            "category": CATEGORIES[4],
            "severity": SEVERITIES[2],
            "status": STATUSES[3],
            "owner": "Lab Operator",
        },
        {
            "id": "SWI-5102",
            "title": "Critical open finding",
            "category": CATEGORIES[2],
            "severity": SEVERITIES[0],
            "status": STATUSES[0],
            "owner": "Lab Operator",
        },
    ]
    for item in items:
        store.insert(item)
    expected = build_summary(store.list_all())
    store.close()

    dash_html = client.get("/").get_data(as_text=True)
    assert card_value(dash_html, "Open Work Items") == expected["open"]
    assert card_value(dash_html, "Critical Findings") == expected["critical"]
    assert card_value(dash_html, "Changes Awaiting Approval") == expected["awaiting_approval"]
    assert card_value(dash_html, "Completed Work") == expected["completed"]


def test_health_endpoint_still_works(sqlite_client):
    client, _db_path = sqlite_client
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"service": "sentinel-app", "status": "healthy"}

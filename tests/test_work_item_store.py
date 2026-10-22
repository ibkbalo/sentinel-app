"""Automated tests for SQLite work-item persistence."""

from pathlib import Path

import pytest

from app import CATEGORIES, SEVERITIES, STATUSES, WORK_ITEMS, app, build_summary
from work_item_store import WorkItemStore, WorkItemStoreError, default_database_path

EXPECTED_SUMMARY = {
    "open": 6,
    "critical": 2,
    "awaiting_approval": 2,
    "completed": 2,
}


def valid_item(**overrides):
    item = {
        "id": "SWI-2001",
        "title": "Remediate exposed admin panel",
        "category": CATEGORIES[0],
        "severity": SEVERITIES[1],
        "status": STATUSES[0],
        "owner": "Lab Operator",
    }
    item.update(overrides)
    return item


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_work_items.db"
    store = WorkItemStore(db_path)
    store.initialize_schema()
    yield store
    store.close()


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_schema_initialization_creates_database_file(tmp_path):
    db_path = tmp_path / "schema.db"
    store = WorkItemStore(db_path)
    assert not db_path.exists()
    store.initialize_schema()
    assert db_path.exists()
    assert store.list_all() == []
    store.close()


def test_repeated_schema_initialization_does_not_lose_data(store):
    store.insert(valid_item())
    store.initialize_schema()
    store.initialize_schema()
    assert store.get_by_id("SWI-2001") is not None
    assert len(store.list_all()) == 1


def test_insert_valid_work_item(store):
    saved = store.insert(valid_item())
    assert saved["id"] == "SWI-2001"
    assert saved["title"] == "Remediate exposed admin panel"
    assert saved["category"] == CATEGORIES[0]


def test_get_by_id(store):
    store.insert(valid_item())
    found = store.get_by_id("SWI-2001")
    assert found is not None
    assert found["owner"] == "Lab Operator"
    assert store.get_by_id("SWI-9999") is None


def test_list_all_returns_all_records(store):
    store.insert(valid_item(id="SWI-2001"))
    store.insert(valid_item(id="SWI-2002", title="Second item"))
    items = store.list_all()
    assert [item["id"] for item in items] == ["SWI-2001", "SWI-2002"]


def test_update_existing_work_item(store):
    store.insert(valid_item())
    updated = store.update(
        valid_item(
            status=STATUSES[2],
            title="Remediate exposed admin panel (updated)",
        )
    )
    assert updated["status"] == "Awaiting Approval"
    assert updated["title"] == "Remediate exposed admin panel (updated)"
    assert store.get_by_id("SWI-2001")["status"] == "Awaiting Approval"


def test_duplicate_id_rejected(store):
    store.insert(valid_item())
    with pytest.raises(WorkItemStoreError) as exc_info:
        store.insert(valid_item(title="Different title"))
    assert any("Duplicate" in error for error in exc_info.value.errors)


def test_invalid_input_rejected_on_insert(store):
    with pytest.raises(WorkItemStoreError) as exc_info:
        store.insert(valid_item(category="Not A Category"))
    assert any("category" in error for error in exc_info.value.errors)
    assert store.list_all() == []

    with pytest.raises(WorkItemStoreError):
        store.insert(valid_item(id="BAD-ID"))
    assert store.list_all() == []

    with pytest.raises(WorkItemStoreError):
        store.insert("not-a-dict")  # type: ignore[arg-type]


def test_invalid_input_rejected_on_update(store):
    store.insert(valid_item())
    with pytest.raises(WorkItemStoreError) as exc_info:
        store.update(valid_item(status="Blocked"))
    assert any("status" in error for error in exc_info.value.errors)
    assert store.get_by_id("SWI-2001")["status"] == "Open"

    with pytest.raises(WorkItemStoreError) as missing:
        store.update(valid_item(id="SWI-4040"))
    assert any("not found" in error for error in missing.value.errors)


def test_parameterized_query_safety_stores_literal_payload(store):
    hostile_title = "'); DROP TABLE work_items;--"
    store.insert(valid_item(title=hostile_title))
    stored = store.get_by_id("SWI-2001")
    assert stored is not None
    assert stored["title"] == hostile_title
    # Table still exists and still holds the row.
    assert len(store.list_all()) == 1


def test_data_survives_connection_close_and_reopen(tmp_path):
    db_path = tmp_path / "persist.db"
    first = WorkItemStore(db_path)
    first.initialize_schema()
    first.insert(valid_item(id="SWI-3001", title="Persisted finding"))
    first.close()

    second = WorkItemStore(db_path)
    second.initialize_schema()
    restored = second.get_by_id("SWI-3001")
    assert restored is not None
    assert restored["title"] == "Persisted finding"
    assert restored["category"] == CATEGORIES[0]
    second.close()


def test_independent_test_databases_are_separated(tmp_path):
    store_a = WorkItemStore(tmp_path / "a.db")
    store_b = WorkItemStore(tmp_path / "b.db")
    store_a.initialize_schema()
    store_b.initialize_schema()

    store_a.insert(valid_item(id="SWI-4001", title="Only in A"))
    store_b.insert(valid_item(id="SWI-4002", title="Only in B"))

    assert store_a.get_by_id("SWI-4001") is not None
    assert store_a.get_by_id("SWI-4002") is None
    assert store_b.get_by_id("SWI-4002") is not None
    assert store_b.get_by_id("SWI-4001") is None

    store_a.close()
    store_b.close()


def test_insert_normalizes_whitespace(store):
    saved = store.insert(
        valid_item(
            id="  SWI-2005  ",
            title="  Trimmed title  ",
            owner="  Operator  ",
        )
    )
    assert saved["id"] == "SWI-2005"
    assert saved["title"] == "Trimmed title"
    assert saved["owner"] == "Operator"


def test_default_database_path_uses_env(monkeypatch, tmp_path):
    configured = tmp_path / "custom" / "app.db"
    monkeypatch.setenv("SENTINEL_APP_DB_PATH", str(configured))
    assert default_database_path() == Path(configured)


def test_existing_flask_behavior_unchanged(client):
    assert build_summary(WORK_ITEMS) == EXPECTED_SUMMARY
    assert client.get("/").status_code == 200
    assert client.get("/work-items").status_code == 200
    health = client.get("/health").get_json()
    assert health == {"service": "sentinel-app", "status": "healthy"}
    html = client.get("/work-items").get_data(as_text=True)
    assert "SWI-1001" in html
    assert "Priya Natarajan" in html

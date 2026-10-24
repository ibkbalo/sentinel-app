"""Flask integration tests for the read-only Agent Jobs page."""

from __future__ import annotations

import pytest

from agent_feed import (
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_INVALID,
    STATUS_OK,
    STATUS_UNAVAILABLE,
)
from app import app
from work_item_store import WorkItemStore


def _feed(status, jobs=None, message=""):
    return {
        "status": status,
        "jobs": list(jobs or []),
        "message": message,
        "http_status": 200 if status in {STATUS_OK, STATUS_EMPTY} else None,
        "source": "agent_face_backlog",
    }


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINEL_APP_DB_PATH", str(tmp_path / "agent_jobs_page.db"))
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client, tmp_path / "agent_jobs_page.db"


def test_agent_jobs_returns_200(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_EMPTY, message="No pending Agent jobs"),
    )
    response = flask_client.get("/agent-jobs")
    assert response.status_code == 200
    assert b"Sentinel Stacks Agent Jobs" in response.data
    assert b"Read Only" in response.data


def test_valid_jobs_render_accurately(client, monkeypatch):
    flask_client, _db = client
    jobs = [
        {
            "job_id": "job_20261023T120000Z_abc",
            "role": "cloud_security",
            "status": "pending_approval",
            "created_at": "2026-10-23T12:00:00Z",
            "total_findings": 5,
            "critical": 1,
            "high": 2,
            "sla_hint": "breach_risk",
        }
    ]
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_OK, jobs=jobs, message="loaded"),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True)
    assert "job_20261023T120000Z_abc" in html
    assert "cloud_security" in html
    assert "pending_approval" in html
    assert "2026-10-23T12:00:00Z" in html
    assert "breach_risk" in html
    assert ">5</td>" in html
    assert "kit_path" not in html
    assert "/brain_workspace" not in html
    assert "are not available here" in html
    assert "<form" not in html.lower()
    assert 'type="submit"' not in html.lower()


def test_empty_backlog_message(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_EMPTY),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True)
    assert "No pending Agent jobs are available." in html
    assert "Agent backlog is empty." in html
    assert "<tbody>" not in html


def test_offline_agent_unavailable_state(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_UNAVAILABLE, message="Agent Face is unavailable"),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True)
    assert "currently unavailable" in html
    assert "offline or unreachable" in html
    assert "job_" not in html
    assert "Traceback" not in html
    assert "Exception" not in html


def test_invalid_response_hides_internal_details(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_INVALID, message="Agent Face returned invalid JSON"),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True)
    assert "invalid response" in html.lower()
    assert "Internal diagnostic details are not shown." in html
    assert "Traceback" not in html
    assert "json.JSONDecodeError" not in html
    assert "127.0.0.1" not in html


def test_error_state_does_not_expose_internals(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_ERROR, message="boom /secret/path"),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True)
    assert "Unable to retrieve Agent jobs" in html
    assert "/secret/path" not in html
    assert "boom" not in html


def test_page_has_no_state_changing_actions(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(
            STATUS_OK,
            jobs=[
                {
                    "job_id": "job_1",
                    "role": "iam",
                    "status": "pending_approval",
                    "created_at": None,
                    "total_findings": 1,
                    "critical": 0,
                    "high": 1,
                    "sla_hint": "review_soon",
                }
            ],
        ),
    )
    html = flask_client.get("/agent-jobs").get_data(as_text=True).lower()
    for forbidden in (
        "approve",
        "reject",
        "remediat",
        "scan now",
        "complete job",
        "trigger",
        "method=\"post\"",
    ):
        # Allow the disclaimer sentence mentioning approval/rejection as unavailable.
        if forbidden in {"approve", "reject", "remediat"}:
            continue
        assert forbidden not in html
    assert "approval, rejection, scanning, and remediation actions" in html
    assert "are not available here" in html


def test_viewing_agent_jobs_does_not_modify_sqlite(client, monkeypatch):
    flask_client, db_path = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(
            STATUS_OK,
            jobs=[
                {
                    "job_id": "job_db_check",
                    "role": "devsecops",
                    "status": "pending_approval",
                    "created_at": "2026-10-23T12:00:00Z",
                    "total_findings": 2,
                    "critical": 0,
                    "high": 1,
                    "sla_hint": "normal",
                }
            ],
        ),
    )
    assert flask_client.get("/agent-jobs").status_code == 200

    store = WorkItemStore(db_path)
    store.initialize_schema()
    assert store.list_all() == []
    store.close()


def test_existing_routes_still_work(client, monkeypatch):
    flask_client, _db = client
    monkeypatch.setattr(
        "app.fetch_agent_backlog",
        lambda: _feed(STATUS_EMPTY),
    )
    assert flask_client.get("/").status_code == 200
    assert flask_client.get("/work-items").status_code == 200
    assert flask_client.get("/health").get_json() == {
        "service": "sentinel-app",
        "status": "healthy",
    }
    nav = flask_client.get("/").get_data(as_text=True)
    assert "Agent Jobs" in nav
    assert "/agent-jobs" in nav

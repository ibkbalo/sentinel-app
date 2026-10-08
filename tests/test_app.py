"""Automated tests for Sentinel App using Flask's built-in test client."""

import re

import pytest

from app import WORK_ITEMS, app, build_summary

EXPECTED_SUMMARY = {
    "open": 6,
    "critical": 2,
    "awaiting_approval": 2,
    "completed": 2,
}


@pytest.fixture
def client():
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


def test_work_items_page_displays_sample_items(client):
    html = client.get("/work-items").get_data(as_text=True)
    assert len(WORK_ITEMS) > 0
    for item in WORK_ITEMS:
        assert item["id"] in html
        assert item["title"] in html
        assert item["owner"] in html


def test_work_items_page_displays_known_item(client):
    html = client.get("/work-items").get_data(as_text=True)
    assert "SWI-1001" in html
    assert "Patch OpenSSL on customer-facing load balancers" in html
    assert "Vulnerability Remediation" in html


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_json(client):
    response = client.get("/health")
    assert response.is_json
    data = response.get_json()
    assert data["service"] == "sentinel-app"
    assert data["status"] == "healthy"


def test_build_summary_matches_sample_data():
    assert build_summary(WORK_ITEMS) == EXPECTED_SUMMARY


def test_dashboard_summary_counts_match_sample_data(client):
    html = client.get("/").get_data(as_text=True)
    assert card_value(html, "Open Work Items") == EXPECTED_SUMMARY["open"]
    assert card_value(html, "Critical Findings") == EXPECTED_SUMMARY["critical"]
    assert (
        card_value(html, "Changes Awaiting Approval")
        == EXPECTED_SUMMARY["awaiting_approval"]
    )
    assert card_value(html, "Completed Work") == EXPECTED_SUMMARY["completed"]

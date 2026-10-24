"""Unit tests for the read-only Agent Face backlog client (mocked HTTP only)."""

from __future__ import annotations

import io
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

import agent_feed
from agent_feed import (
    FIXED_HOST,
    FIXED_PATH,
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_INVALID,
    STATUS_OK,
    STATUS_UNAVAILABLE,
    backlog_url,
    configured_face_port,
    fetch_agent_backlog,
    normalize_backlog_item,
)


class _FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self._buffer = io.BytesIO(body)
        self.status = status
        self._code = status

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def getcode(self) -> int:
        return self._code

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeOpener:
    def __init__(self, handler):
        self._handler = handler
        self.last_request: Request | None = None

    def open(self, request, timeout=None):
        self.last_request = request
        return self._handler(request, timeout)


def _patch_opener(monkeypatch, handler):
    opener = _FakeOpener(handler)

    def fake_build_opener(*_handlers):
        return opener

    monkeypatch.setattr(agent_feed, "build_opener", fake_build_opener)
    return opener


def _sample_job(**overrides):
    job = {
        "job_id": "job_20261023T120000Z_abc123",
        "role": "cloud_security",
        "status": "pending_approval",
        "created_at": "2026-10-23T12:00:00Z",
        "total_findings": 4,
        "critical": 1,
        "high": 2,
        "sla_hint": "breach_risk",
        "kit_path": "/secret/workspace/kits/job_abc",
        "top_finding_ids": ["FIND-1", "FIND-2"],
        "workspace": "/secret/brain_workspace",
    }
    job.update(overrides)
    return job


def test_backlog_url_is_fixed_loopback():
    assert backlog_url(5050) == "http://127.0.0.1:5050/api/backlog"
    assert FIXED_HOST == "127.0.0.1"
    assert FIXED_PATH == "/api/backlog"


def test_configured_port_default(monkeypatch):
    monkeypatch.delenv("SENTINEL_AGENT_FACE_PORT", raising=False)
    assert configured_face_port() == 5050


def test_configured_port_from_env(monkeypatch):
    monkeypatch.setenv("SENTINEL_AGENT_FACE_PORT", "5051")
    assert configured_face_port() == 5051
    assert backlog_url() == "http://127.0.0.1:5051/api/backlog"


def test_invalid_port_configuration(monkeypatch):
    monkeypatch.setenv("SENTINEL_AGENT_FACE_PORT", "not-a-port")
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_ERROR
    assert "65535" in result["message"]

    monkeypatch.setenv("SENTINEL_AGENT_FACE_PORT", "70000")
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_ERROR

    result = fetch_agent_backlog(port=0)
    assert result["status"] == STATUS_ERROR


def test_valid_backlog_response(monkeypatch):
    body = json.dumps({"backlog": [_sample_job()]}).encode("utf-8")

    def handler(request, timeout):
        assert request.get_method() == "GET"
        assert request.full_url == "http://127.0.0.1:5050/api/backlog"
        return _FakeResponse(body)

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_OK
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["job_id"] == "job_20261023T120000Z_abc123"
    assert result["jobs"][0]["critical"] == 1
    assert result["http_status"] == 200


def test_multiple_jobs(monkeypatch):
    body = json.dumps(
        {
            "backlog": [
                _sample_job(job_id="job_a", critical=2),
                _sample_job(job_id="job_b", critical=0, high=1, sla_hint="review_soon"),
            ]
        }
    ).encode("utf-8")
    _patch_opener(monkeypatch, lambda request, timeout: _FakeResponse(body))
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_OK
    assert [job["job_id"] for job in result["jobs"]] == ["job_a", "job_b"]


def test_empty_backlog(monkeypatch):
    body = json.dumps({"backlog": []}).encode("utf-8")
    _patch_opener(monkeypatch, lambda request, timeout: _FakeResponse(body))
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_EMPTY
    assert result["jobs"] == []


def test_connection_refused(monkeypatch):
    def handler(request, timeout):
        raise URLError(ConnectionRefusedError(10061, "Connection refused"))

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_UNAVAILABLE
    assert "unavailable" in result["message"].lower()


def test_timeout(monkeypatch):
    def handler(request, timeout):
        raise URLError(socket.timeout("timed out"))

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_UNAVAILABLE
    assert "timed out" in result["message"].lower()


def test_invalid_json(monkeypatch):
    _patch_opener(
        monkeypatch, lambda request, timeout: _FakeResponse(b"not-json{")
    )
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_INVALID


def test_invalid_response_structure(monkeypatch):
    _patch_opener(
        monkeypatch,
        lambda request, timeout: _FakeResponse(json.dumps({"jobs": []}).encode()),
    )
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_INVALID

    _patch_opener(
        monkeypatch,
        lambda request, timeout: _FakeResponse(
            json.dumps({"backlog": "not-a-list"}).encode()
        ),
    )
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_INVALID


def test_missing_job_id_skipped(monkeypatch):
    body = json.dumps(
        {
            "backlog": [
                _sample_job(job_id=""),
                {"role": "cloud_security", "critical": 9},
                _sample_job(job_id="job_ok"),
            ]
        }
    ).encode("utf-8")
    _patch_opener(monkeypatch, lambda request, timeout: _FakeResponse(body))
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_OK
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["job_id"] == "job_ok"


def test_missing_job_id_only_yields_empty(monkeypatch):
    body = json.dumps({"backlog": [{"role": "x", "critical": 1}]}).encode()
    _patch_opener(monkeypatch, lambda request, timeout: _FakeResponse(body))
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_EMPTY
    assert result["jobs"] == []


def test_http_error(monkeypatch):
    def handler(request, timeout):
        raise HTTPError(
            request.full_url,
            503,
            "Service Unavailable",
            hdrs=None,
            fp=io.BytesIO(b""),
        )

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_ERROR
    assert result["http_status"] == 503


def test_redirect_rejection(monkeypatch):
    def handler(request, timeout):
        raise URLError("Refusing HTTP redirect from Agent Face (HTTP 302)")

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog()
    assert result["status"] == STATUS_ERROR
    assert "redirect" in result["message"].lower()


def test_field_filtering_excludes_sensitive_keys():
    normalized = normalize_backlog_item(_sample_job())
    assert normalized is not None
    assert set(normalized) == {
        "job_id",
        "role",
        "status",
        "created_at",
        "total_findings",
        "critical",
        "high",
        "sla_hint",
    }
    assert "kit_path" not in normalized
    assert "workspace" not in normalized
    assert "top_finding_ids" not in normalized


def test_does_not_invent_severity_counts():
    normalized = normalize_backlog_item(
        {
            "job_id": "job_x",
            "critical": "nope",
            "high": None,
            "total_findings": -3,
        }
    )
    assert normalized is not None
    assert normalized["critical"] is None
    assert normalized["high"] is None
    assert normalized["total_findings"] is None


def test_get_only_and_fixed_loopback(monkeypatch):
    captured = {}

    def handler(request, timeout):
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        body = json.dumps({"backlog": []}).encode()
        return _FakeResponse(body)

    _patch_opener(monkeypatch, handler)
    fetch_agent_backlog(port=5050)
    assert captured["method"] == "GET"
    assert captured["url"].startswith("http://127.0.0.1:")
    assert captured["url"].endswith("/api/backlog")
    assert "approve" not in captured["url"]
    assert "reject" not in captured["url"]
    assert "cycle" not in captured["url"]


def test_oversized_response(monkeypatch):
    def handler(request, timeout):
        return _FakeResponse(b"x" * 100)

    _patch_opener(monkeypatch, handler)
    result = fetch_agent_backlog(max_bytes=50)
    assert result["status"] == STATUS_INVALID

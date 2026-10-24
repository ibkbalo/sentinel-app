"""Read-only Sentinel Stacks Agent Face backlog client.

Fetches GET http://127.0.0.1:<port>/api/backlog only. Never accepts user-supplied
hosts or URLs, never follows redirects, and never calls state-changing Agent
endpoints. Does not write SQLite or Agent workspace data.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

logger = logging.getLogger(__name__)

FIXED_HOST = "127.0.0.1"
FIXED_PATH = "/api/backlog"
DEFAULT_PORT = 5050
PORT_ENV_VAR = "SENTINEL_AGENT_FACE_PORT"
DEFAULT_TIMEOUT_SECONDS = 3.0
MAX_RESPONSE_BYTES = 1_048_576  # 1 MiB

STATUS_OK = "ok"
STATUS_EMPTY = "empty"
STATUS_UNAVAILABLE = "unavailable"
STATUS_INVALID = "invalid"
STATUS_ERROR = "error"

_DISPLAY_FIELDS = (
    "job_id",
    "role",
    "status",
    "created_at",
    "total_findings",
    "critical",
    "high",
    "sla_hint",
)


class _RejectRedirects(HTTPRedirectHandler):
    """Refuse all HTTP redirects so the client cannot leave loopback."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise URLError(f"Refusing HTTP redirect from Agent Face (HTTP {code})")


def configured_face_port() -> int:
    """Return the Agent Face port from env or default; raise ValueError if invalid."""
    raw = os.environ.get(PORT_ENV_VAR)
    if raw is None or str(raw).strip() == "":
        return DEFAULT_PORT
    try:
        port = int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{PORT_ENV_VAR} must be an integer between 1 and 65535"
        ) from exc
    if port < 1 or port > 65535:
        raise ValueError(
            f"{PORT_ENV_VAR} must be an integer between 1 and 65535"
        )
    return port


def resolve_face_port(port: int | None = None) -> int:
    """Resolve an explicit port or the configured environment port."""
    if port is None:
        return configured_face_port()
    if not isinstance(port, int) or isinstance(port, bool) or port < 1 or port > 65535:
        raise ValueError("port must be an integer between 1 and 65535")
    return port


def backlog_url(port: int | None = None) -> str:
    """Build the fixed loopback backlog URL (host and path are not configurable)."""
    resolved = resolve_face_port(port)
    return f"http://{FIXED_HOST}:{resolved}{FIXED_PATH}"


def _as_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def normalize_backlog_item(raw: Any) -> dict[str, Any] | None:
    """Normalize one backlog row for display, or None if unusable.

    Requires a non-empty string job_id. Does not invent severity counts.
    Omits kit_path and any non-display fields.
    """
    if not isinstance(raw, dict):
        return None
    job_id = raw.get("job_id")
    if not isinstance(job_id, str) or not job_id.strip():
        return None

    item: dict[str, Any] = {"job_id": job_id.strip()}

    role = raw.get("role")
    item["role"] = role.strip() if isinstance(role, str) and role.strip() else None

    status = raw.get("status")
    item["status"] = (
        status.strip() if isinstance(status, str) and status.strip() else None
    )

    created_at = raw.get("created_at")
    item["created_at"] = (
        created_at.strip()
        if isinstance(created_at, str) and created_at.strip()
        else None
    )

    item["total_findings"] = _as_non_negative_int(raw.get("total_findings"))
    item["critical"] = _as_non_negative_int(raw.get("critical"))
    item["high"] = _as_non_negative_int(raw.get("high"))

    sla_hint = raw.get("sla_hint")
    item["sla_hint"] = (
        sla_hint.strip() if isinstance(sla_hint, str) and sla_hint.strip() else None
    )

    return {key: item[key] for key in _DISPLAY_FIELDS}


def _feed_result(
    status: str,
    *,
    jobs: list[dict[str, Any]] | None = None,
    message: str = "",
    http_status: int | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "jobs": list(jobs or []),
        "message": message,
        "http_status": http_status,
        "source": "agent_face_backlog",
    }


def _read_limited(response: Any, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(65536, max(0, limit - total + 1)))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError("Agent Face response exceeds size limit")
        chunks.append(chunk)
    return b"".join(chunks)


def fetch_agent_backlog(
    *,
    port: int | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> dict[str, Any]:
    """GET the Agent Face backlog and return a normalized result dict.

    Does not log response bodies. Does not follow redirects.
    """
    try:
        resolved_port = resolve_face_port(port)
        url = backlog_url(resolved_port)
    except ValueError as exc:
        logger.warning("Invalid Agent Face port configuration")
        return _feed_result(STATUS_ERROR, message=str(exc))

    request = Request(url, method="GET", headers={"Accept": "application/json"})
    opener = build_opener(_RejectRedirects)

    try:
        with opener.open(request, timeout=timeout) as response:
            http_status = getattr(response, "status", None) or response.getcode()
            raw = _read_limited(response, max_bytes)
    except HTTPError as exc:
        logger.warning("Agent Face HTTP error status=%s", exc.code)
        return _feed_result(
            STATUS_ERROR,
            message="Agent Face returned an HTTP error",
            http_status=exc.code,
        )
    except (TimeoutError, socket.timeout):
        logger.warning("Agent Face request timed out")
        return _feed_result(
            STATUS_UNAVAILABLE,
            message="Agent Face request timed out",
        )
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            logger.warning("Agent Face request timed out")
            return _feed_result(
                STATUS_UNAVAILABLE,
                message="Agent Face request timed out",
            )
        if "Refusing HTTP redirect" in str(exc):
            logger.warning("Agent Face attempted an HTTP redirect")
            return _feed_result(
                STATUS_ERROR,
                message="Agent Face redirect was rejected",
            )
        reason_text = str(reason).lower()
        if (
            isinstance(reason, ConnectionRefusedError)
            or getattr(reason, "errno", None) in {111, 10061}
            or "refused" in reason_text
        ):
            logger.warning("Agent Face connection refused")
            return _feed_result(
                STATUS_UNAVAILABLE,
                message="Agent Face is unavailable",
            )
        if "timed out" in reason_text:
            logger.warning("Agent Face request timed out")
            return _feed_result(
                STATUS_UNAVAILABLE,
                message="Agent Face request timed out",
            )
        logger.warning("Agent Face connection error")
        return _feed_result(
            STATUS_UNAVAILABLE,
            message="Agent Face is unavailable",
        )
    except ValueError:
        logger.warning("Agent Face response rejected")
        return _feed_result(
            STATUS_INVALID,
            message="Agent Face response was too large or invalid",
        )
    except OSError:
        logger.warning("Agent Face connection error")
        return _feed_result(
            STATUS_UNAVAILABLE,
            message="Agent Face is unavailable",
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Agent Face returned invalid JSON")
        return _feed_result(
            STATUS_INVALID,
            message="Agent Face returned invalid JSON",
            http_status=http_status,
        )

    if not isinstance(payload, dict) or "backlog" not in payload:
        logger.warning("Agent Face response missing backlog")
        return _feed_result(
            STATUS_INVALID,
            message="Agent Face response structure was invalid",
            http_status=http_status,
        )

    backlog = payload.get("backlog")
    if not isinstance(backlog, list):
        logger.warning("Agent Face backlog is not a list")
        return _feed_result(
            STATUS_INVALID,
            message="Agent Face response structure was invalid",
            http_status=http_status,
        )

    jobs: list[dict[str, Any]] = []
    skipped = 0
    for entry in backlog:
        normalized = normalize_backlog_item(entry)
        if normalized is None:
            skipped += 1
            continue
        jobs.append(normalized)

    if skipped:
        logger.warning("Skipped %s invalid Agent backlog record(s)", skipped)

    if not jobs:
        return _feed_result(
            STATUS_EMPTY,
            jobs=[],
            message="No pending Agent jobs",
            http_status=http_status,
        )

    return _feed_result(
        STATUS_OK,
        jobs=jobs,
        message="Agent backlog loaded",
        http_status=http_status,
    )

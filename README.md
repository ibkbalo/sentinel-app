# Sentinel App

**Sentinel Stacks — Security Work Management**

Sentinel App is an internal web application used by Sentinel Stacks employees to
manage company security work items. It is a standalone business application and
is separate from the Sentinel Stacks security platform.

## Business Purpose

Security work at Sentinel Stacks comes from many sources. Sentinel App gives
employees one place to create and track that work, including:

- Vulnerability remediation
- Security configuration changes
- Cloud security findings
- DevSecOps findings
- Incident follow-up work

## Phase 1 Architecture

Phase 1 is intentionally small:

- **Python Flask** application (`app.py`) serving server-rendered pages.
- **Jinja2 templates** (`templates/`) for the HTML views.
- **Plain CSS** (`static/style.css`) for styling. No JavaScript framework.
- **In-memory sample data** defined in `app.py`. No database.
- No authentication, external APIs, cloud services, or secrets.

| Route         | Description                                      |
|---------------|--------------------------------------------------|
| `/`           | Dashboard with summary cards                     |
| `/work-items` | Table of sample security work items              |
| `/health`     | JSON health check: `{"service": "sentinel-app", "status": "healthy"}` |

### Current application status (verified)

- Flask-based internal human staff work-management application.
- Human-first design; one person currently performs the staff roles.
- The application remains in development.
- Work-item data is currently in memory, not persistent storage.
- No AI staff integration is implemented or assumed.

```
sentinel-app/
├── .dockerignore
├── .github/
│   └── workflows/
│       └── ci.yml
├── Dockerfile
├── compose.yaml
├── app.py
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── static/
│   └── style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   └── work_items.html
└── tests/
    └── test_app.py
```

## Running Locally

Requires Python 3.11+.

**Windows (PowerShell):**

```powershell
cd sentinel-app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

**macOS / Linux:**

```bash
cd sentinel-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000> in your browser. The health check is at
<http://127.0.0.1:5000/health>.

## Running Tests

Tests use pytest and Flask's built-in test client, so no running server,
database, or external services are needed. With the virtual environment active:

```bash
pip install -r requirements-dev.txt
python -m pytest -v
```

## Running with Docker (local development)

The `Dockerfile` builds a single-stage image from a pinned slim Python 3.11
base. It installs only `requirements.txt` (Flask and Gunicorn), runs as a
dedicated non-root user, and serves the app with Gunicorn on port 8000. A
built-in health check calls `/health` using Python's standard library.

This setup is for one-user local development and is not production-ready.

**Windows (PowerShell)**, from the `sentinel-app` folder:

```powershell
# Build the image
docker build -t sentinel-app:local .

# Run the container, reachable only from this machine (127.0.0.1)
docker run -d --name sentinel-app-test -p 127.0.0.1:8081:8000 sentinel-app:local

# Confirm the container is running (STATUS shows "healthy" after ~30 seconds)
docker ps --filter "name=sentinel-app-test"

# Verify the health endpoint
Invoke-RestMethod http://127.0.0.1:8081/health

# Check Docker's health check status
docker inspect --format "{{.State.Health.Status}}" sentinel-app-test

# View Gunicorn logs
docker logs sentinel-app-test

# Stop and remove the test container
docker stop sentinel-app-test
docker rm sentinel-app-test
```

While the container runs, open <http://127.0.0.1:8081> in your browser.

## Phase 4 — Ubuntu infrastructure deployment (verified)

The following describes the completed Phase 4 lab deployment and recovery
validation. It records verified facts only. Planned future work is called out
separately where relevant.

### Ubuntu hosting environment

| Item | Verified value |
|------|----------------|
| Guest OS | Ubuntu 22.04.5 LTS (VirtualBox) |
| Host name | `splunk-server` |
| pfSense LAN address | `192.168.5.246` |
| Host-only SSH address | `192.168.56.105` |
| SSH username | `ibk` |
| pfSense gateway | `192.168.5.1` |
| Docker Engine | 29.1.3 |
| Docker Compose | 2.40.3 |
| Deployment directory | `~/sentinel-app` |

### Docker Compose deployment

Repository configuration (`compose.yaml`) matches the verified Ubuntu deployment:

- **Image:** `sentinel-app:ubuntu` (built from the existing `Dockerfile`)
- **Container name:** `sentinel-app-sentinel-app-1`
- **Port mapping:** host `127.0.0.1:8081` → container `8000`
- **Restart policy:** `unless-stopped`
- **Health check:** defined in the `Dockerfile` only (not duplicated in Compose)
- **Docker systemd service:** enabled on Ubuntu
- **Container health:** verified as healthy

From `~/sentinel-app` on Ubuntu, use Compose V2 with `sudo` where required:

```bash
# Start (build if needed)
sudo docker compose up -d --build

# Inspect running services / containers
sudo docker compose ps
sudo docker ps --filter "name=sentinel-app"

# View application logs
sudo docker compose logs -f sentinel-app

# Stop the application (container remains unless removed)
sudo docker compose stop

# Stop and remove Compose resources for this project
sudo docker compose down
```

Health status can also be checked with:

```bash
sudo docker inspect --format '{{.State.Health.Status}}' sentinel-app-sentinel-app-1
```

### Windows SSH access (localhost tunnel)

The application listens only on Ubuntu localhost (`127.0.0.1:8081`). It is not
publicly exposed. Remote browser access from Windows uses an SSH local
forward.

**Verified Windows PowerShell command:**

```powershell
ssh -N -L 8081:127.0.0.1:8081 ibk@192.168.56.105
```

With the tunnel open, open the app in a browser at:

<http://127.0.0.1:8081>

### Wazuh host monitoring (verified)

| Item | Verified value |
|------|----------------|
| Wazuh Manager | `192.168.5.250` |
| Manager version | 4.14.8 |
| Ubuntu agent name | `sentinel-ubuntu-01` |
| Agent ID | `004` |
| Agent version | 4.14.8 |
| Agent service | `wazuh-agent` |
| Startup | Agent enabled at startup |
| Connectivity | Connected to Manager over TCP port **1514** |

Agent monitoring is **host-level**. Full Docker/container security monitoring
has **not** been configured.

### Verified infrastructure recovery test — October 20, 2026

This was a **planned shutdown/startup recovery validation**, not a full
disaster recovery or backup/restore test.

Procedure: the Ubuntu VM was shut down cleanly and powered on again.

**Verified results:**

- Ubuntu booted successfully.
- SSH access restored.
- Docker service started automatically.
- Sentinel App container started automatically.
- Container reported healthy.
- `/health` returned HTTP 200.
- `/` returned HTTP 200.
- `/work-items` returned HTTP 200.
- Wazuh Agent service returned active.
- Wazuh Agent successfully reconnected to `192.168.5.250:1514/tcp`.
- Windows browser access through the SSH tunnel was successful.
- Existing application pages rendered correctly.

### CI security checks

GitHub Actions workflow: `.github/workflows/ci.yml`.

Triggers: pushes and pull requests targeting `main`. Runner: `ubuntu-latest`
with Python 3.11. Permissions: `contents: read`.

| Job ID | Display name | Check |
|--------|--------------|-------|
| `test` | Run tests | **Pytest** (`python -m pytest -v`) |
| `sast` | Bandit SAST | **Bandit** (medium+ severity fails the job) |
| `dependency-audit` | Dependency Audit (pip-audit) | **pip-audit** against `requirements-dev.txt` |
| `secret-scan` | Gitleaks Secret Scan | **Gitleaks** (full git history, redacted output) |

All four checks were **passing at the last verified checkpoint**. This document
does not claim they are currently passing without a new CI run.

### Known deferred security finding — DEVSECOPS-001

Baseline from a previously recorded Trivy container-image scan:

- **95 HIGH/CRITICAL** findings.
- Remediation is **intentionally deferred** to a dedicated learning/remediation
  phase.
- This baseline is **not** evidence that the findings have been resolved.
- No new scan was performed as part of writing this documentation, and
  dependencies were not modified for this baseline.

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

```
sentinel-app/
├── .dockerignore
├── Dockerfile
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    └── work_items.html
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

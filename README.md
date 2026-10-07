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
├── app.py
├── requirements.txt
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

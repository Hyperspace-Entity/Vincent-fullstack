# Vincent Backend — fresh start

A complete, working Flask backend for the review-queue feature — no
guessing about where `db` lives this time, since this is the whole project.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Visit `http://localhost:5000/health` — you should see `{"status": "ok"}`.
The database (`instance/vincent.db`) is created automatically on first run.

## Connect the frontend

Open `vincent-app.html`, paste `http://localhost:5000/api` into the
**Backend URL** field, hit **Connect**.

## What's here

```
run.py                       entry point
requirements.txt
app/
  __init__.py                app factory — creates app, db, CORS, blueprint
  config.py                  SQLite config (instance/vincent.db)
  extensions.py              the one true `db = SQLAlchemy()` instance
  review_queue/
    __init__.py               blueprint definition
    models.py                 Document, Template, RiskFlag, AuditEntry
    risk.py                   risk-of-error scoring logic
    routes.py                 all the API endpoints
instance/                    SQLite DB lives here (auto-created, gitignore this)
```

## Honest gaps (same as before, still true)

- No auth enforcement — every route is open.
- Frontend doesn't do a live refetch of the queue; actions write to the
  API but the list you see is still local browser state.
- Downstream actions on approval (actually sending/filing documents) are
  a `# TODO` in `routes.py`.
- This is a fresh project — it does not contain whatever was in your
  original Vincent codebase (auth, validators, tests, etc.). If that
  turns up later, you'll want to merge this feature into it rather than
  keep them as two separate projects.

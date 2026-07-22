# Wiring `review_queue` into Vincent (Flask version)

This is a Flask blueprint, built to match your project's structure: an
`app/` package, `run.py` entry point, `instance/` config folder.

## 1. Install dependencies

In your activated virtual environment:

```bash
pip install flask-cors
```
(You almost certainly already have `flask` and `flask_sqlalchemy` installed
— this blueprint reuses your existing `db` object rather than creating a
new one.)

## 2. Drop the folder in

Copy the whole `review_queue/` folder so it sits **inside** your `app/`
package, next to your other modules:

```
app/
  __init__.py
  review_queue/        <- goes here
    __init__.py
    models.py
    risk.py
    routes.py
  ...(your existing stuff)
```

## 3. Fix one import

Open `app/review_queue/models.py` and look at the top:

```python
try:
    from app.extensions import db
except ImportError:
    from app import db
```

This guesses where your `db = SQLAlchemy()` instance lives. If neither
guess matches your project, change this line to import `db` from wherever
it actually is — it's the one thing I couldn't know without seeing your
`app/__init__.py`.

## 4. Register the blueprint

In `app/__init__.py`, wherever your app factory creates the app and
registers other blueprints, add:

```python
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    ...
    CORS(app)  # dev only — restrict origins before production

    from app.review_queue import review_queue_bp
    app.register_blueprint(review_queue_bp, url_prefix="/api")

    return app
```

That `/api` prefix is what the frontend's "Backend URL" field should point
at — e.g. `http://localhost:5000/api` (Flask's default port is 5000, not
Django's 8000 — check what `run.py` actually uses).

## 5. Create the tables

Since this defines new models, they need to exist in your database. If
your project uses Flask-Migrate:

```bash
flask db migrate -m "add review queue tables"
flask db upgrade
```

If you're not using migrations yet and it's fine to just create tables
directly (common for early-stage projects), you can do it once from a
Python shell:

```bash
flask shell
```
```python
from app.review_queue.models import db
db.create_all()
exit()
```

## 6. Run it

```bash
python run.py
```
(or however you currently start Vincent's backend — check `run.py` for the
actual command if it's not this simple)

## 7. Point the frontend at it

Open `vincent-app.html`, paste your backend's real address (e.g.
`http://localhost:5000/api`) into the **Backend URL** field, hit
**Connect**.

## Auth

Reviewer identity currently falls back to whatever's typed in the
frontend's "Reviewer" field. `_reviewer_name()` in `routes.py` already
checks for Flask-Login's `current_user` first, so if Vincent already has
user accounts via Flask-Login, reviewer attribution will use real logged-in
usernames automatically — no other changes needed. If Vincent doesn't have
auth yet, this still works fine with the free-text fallback for now.

## What's NOT done for you

- **No auth enforcement.** Every route is open right now — nothing checks
  who's calling it. Add `@login_required` (from Flask-Login) to routes
  once you're ready to lock this down.
- **The frontend still doesn't do a full live refetch of the queue.**
  Actions call this API, but the list you see in the browser is local
  state, not a live server fetch. Worth fixing before this touches real
  documents.
- **Downstream actions on approval** (actually sending/filing the
  document) are a `# TODO` in `routes.py::queue_approve` — specific to
  what Vincent needs to do per doc_type, and wasn't specified.
- **CORS is wide open** (`CORS(app)` with no restrictions) for local dev
  convenience. Restrict it to your actual frontend origin before this
  goes anywhere near production.

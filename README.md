# Drink Tracker

Track daily alcoholic drink counts on a color-coded calendar. Each user has their own login and only sees their own data.

- 0 drinks = green
- 1-3 drinks = yellow
- 4-6 drinks = purple
- 7+ drinks = black

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://127.0.0.1:5050, register an account, and start logging days by clicking on the calendar.

By default, data is stored in a local SQLite file at `instance/drinks.db` (created automatically). Set a `DATABASE_URL` environment variable to point at Postgres instead (used automatically in production, see below).

## Deploying to Render

This repo includes a `render.yaml` Blueprint that provisions both the web service and a free Postgres database in one step:

1. Push this repo to GitHub.
2. In the Render dashboard: **New > Blueprint**, then select this repo. Render reads `render.yaml` and creates:
   - a web service (`drink-tracker`) running `gunicorn app:app`
   - a free Postgres database (`drink-tracker-db`)
   - a random `SECRET_KEY`, and wires `DATABASE_URL` from the database to the web service automatically
3. Click **Apply** and wait for the first deploy to finish, then open the service URL.

No manual environment variable setup needed — the Blueprint handles `SECRET_KEY` and `DATABASE_URL` for you. Tables are created automatically on first boot (`db.create_all()`), so there's no separate migration step to run.

### Deploying without the Blueprint

If you'd rather click things through manually instead of using `render.yaml`:

1. Create a Postgres database on Render (or Supabase/Neon/etc.) and copy its connection string.
2. Create a Web Service pointing at this repo with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
3. Set environment variables on the web service:
   - `SECRET_KEY` — any long random string (e.g. `python3 -c "import secrets; print(secrets.token_hex(32))"`)
   - `DATABASE_URL` — the Postgres connection string from step 1

### Deploying elsewhere

This is a standard Flask app, so it also works on Railway, Fly.io, or any host that runs Python — same `SECRET_KEY` / `DATABASE_URL` env vars apply. If you stick with SQLite instead of Postgres on one of those, make sure the host mounts a **persistent volume** for the `instance/` directory — otherwise the database resets on every deploy or restart.

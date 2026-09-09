# Drink Tracker

Track daily alcoholic drink counts on a color-coded calendar. Each user has their own login and only sees their own data.

- 0 drinks = green
- 1-3 drinks = yellow
- 4-6 drinks = purple
- 7+ drinks = black

Users can add their email in Settings to get a daily reminder at 8am asking them to log last night's drinks; the link in the email opens the calendar with that day ready to fill in.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://127.0.0.1:5050, register an account, and start logging days by clicking on the calendar.

By default, data is stored in a local SQLite file at `instance/drinks.db` (created automatically). Set a `DATABASE_URL` environment variable to point at Postgres instead (used automatically in production, see below).

To test the reminder endpoint locally without real SMTP credentials, set `MAIL_SUPPRESS_SEND=true` — Flask-Mail will skip actually sending. The endpoint only sends between 8:00 and 8:59am in `APP_TIMEZONE` (default `America/New_York`), so outside that window it just reports `{"skipped": true}`:

```bash
curl -X POST http://127.0.0.1:5050/tasks/send-reminders -H "X-Cron-Secret: <your CRON_SECRET>"
```

## Deploying to Render

This repo includes a `render.yaml` Blueprint that provisions both the web service and a free Postgres database in one step:

1. Push this repo to GitHub.
2. In the Render dashboard: **New > Blueprint**, then select this repo. Render reads `render.yaml` and creates:
   - a web service (`drink-tracker`) running `gunicorn app:app`
   - a free Postgres database (`drink-tracker-db`)
   - a random `SECRET_KEY`, and wires `DATABASE_URL` from the database to the web service automatically
3. Click **Apply** and wait for the first deploy to finish, then open the service URL.

The Blueprint handles `SECRET_KEY`, `DATABASE_URL`, and `CRON_SECRET` for you automatically. Tables are created automatically on first boot (`db.create_all()`), so there's no separate migration step to run.

You'll still need to fill in a few values by hand in the Render dashboard after the first deploy (the Blueprint leaves these blank for you to set):

- `APP_BASE_URL` — the URL Render gives your service (e.g. `https://drink-tracker.onrender.com`), used to build the link in reminder emails.
- `MAIL_USERNAME` / `MAIL_PASSWORD` / `MAIL_DEFAULT_SENDER` — see **Setting up email reminders** below.

### Setting up email reminders (Gmail)

The daily reminder emails send via Gmail SMTP using an **App Password** (not your normal Gmail password):

1. Turn on 2-Step Verification on the Google account you want to send from, if it isn't already: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords and create an app password (name it something like "Drink Tracker").
3. In Render, set on the web service:
   - `MAIL_USERNAME` — the full Gmail address
   - `MAIL_PASSWORD` — the 16-character app password Google gave you
   - `MAIL_DEFAULT_SENDER` — usually the same as `MAIL_USERNAME`

### Setting up the daily 8am trigger (GitHub Actions)

Render's free web service tier has no built-in scheduler, so a workflow in this repo (`.github/workflows/daily-reminder.yml`) calls a protected endpoint every hour; the endpoint itself only sends when it's actually 8am in `APP_TIMEZONE`, and tracks who's already been emailed that day, so it's safe to call repeatedly.

In this repo's GitHub Settings → Secrets and variables → Actions, add:

- `APP_URL` — your Render service URL (e.g. `https://drink-tracker.onrender.com`), no trailing slash
- `CRON_SECRET` — copy the value Render generated for the `CRON_SECRET` env var on the web service

Once both secrets are set, the workflow runs automatically (or trigger it manually from the Actions tab with "Run workflow" to test it).

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

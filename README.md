# Drink Tracker

Track daily alcoholic drink counts on a color-coded calendar. Each user has their own login and only sees their own data.

- 0 drinks = green
- 1-3 drinks = yellow
- 4-6 drinks = purple
- 7+ drinks = black

Users can add their email in Settings to get a daily reminder between 7:30 and 8:30am asking them to log last night's drinks; the link in the email opens the calendar with that day ready to fill in.

Each day can also have a short journal entry (a "check-in"), independent of the drink count. Days with a check-in show a small dot on the calendar. The **Check-ins** tab lists every entry by date, sortable by most recent or oldest.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://127.0.0.1:5050, register an account, and start logging days by clicking on the calendar.

By default, data is stored in a local SQLite file at `instance/drinks.db` (created automatically). Set a `DATABASE_URL` environment variable to point at Postgres instead (used automatically in production, see below).

To test the reminder endpoint locally without a real Resend API key, set `MAIL_SUPPRESS_SEND=true` — it'll skip actually sending. The endpoint only sends between 7:30 and 8:30am in `APP_TIMEZONE` (default `America/New_York`), so outside that window it just reports `{"skipped": true}`:

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
- `RESEND_API_KEY` — see **Setting up email reminders** below.

### Setting up email reminders (Resend)

Reminder emails send via [Resend](https://resend.com)'s HTTPS API rather than SMTP — **Render blocks outbound SMTP (ports 25/465/587) on free web services entirely**, so a plain Gmail-SMTP setup will hang every send until it times out. Resend's free tier (100 emails/day) works over HTTPS, which isn't affected by that block.

1. Create a free account at https://resend.com.
2. Go to **API Keys** and create one, then set it in Render as `RESEND_API_KEY`.
3. Without verifying your own domain, Resend only allows sending **from** `onboarding@resend.dev` **to the email address you signed up with** (a sandbox restriction to prevent abuse) — fine for personal use or testing. `MAIL_DEFAULT_SENDER` already defaults to `onboarding@resend.dev` in `render.yaml`.
4. To send reminders to other users later, verify a domain you own in Resend (Domains → Add Domain, then add the DNS records they give you), and set `MAIL_DEFAULT_SENDER` to an address on that domain.

### Setting up the daily morning trigger (external cron service)

Render's free web service tier has no built-in scheduler. This used to be handled by a GitHub Actions workflow, but GitHub's `schedule` trigger turned out to silently throttle frequent cron jobs to run only every few hours regardless of the configured interval (a known platform limitation, not something fixable from this repo) — so it could miss the morning window entirely on a given day. A dedicated free cron-ping service doesn't have that problem.

Using **[cron-job.org](https://cron-job.org)** (free, no card required):

1. Create a free account.
2. Create a new cron job with:
   - **URL**: `https://<your-render-url>/tasks/send-reminders` (e.g. `https://drink-tracker-lv0i.onrender.com/tasks/send-reminders`)
   - **Request method**: `POST`
   - **Custom header**: `X-Cron-Secret: <value>` — use the `CRON_SECRET` Render generated for the web service (find it in the Render dashboard → the service → Environment tab)
   - **Schedule**: every 15 minutes (the endpoint itself only actually sends between 7:30 and 8:30am in `APP_TIMEZONE`, and tracks who's already been emailed that day — so calling it every 15 minutes around the clock is harmless, it's a no-op outside the window and safe to repeat inside it)
3. Save and enable the job.

Any other free "ping a URL on a schedule" service (EasyCron, UptimeRobot's monitor-as-a-trigger, etc.) works the same way — same URL, method, and header.

To test manually without waiting for the schedule:

```bash
curl -X POST https://<your-render-url>/tasks/send-reminders -H "X-Cron-Secret: <your CRON_SECRET>"
```

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

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

from .mailer import send_reminder_email
from .models import User, db

bp = Blueprint("tasks", __name__)

# Temporarily set to 10-11am for a live test send (2026-09-13) — revert to
# 7:30-8:30 once confirmed working. A window rather than an exact minute
# tolerates trigger jitter; per-user last_reminder_sent_date tracking keeps
# it to once a day regardless of how many times the trigger fires inside it.
REMINDER_WINDOW_START = time(10, 0)
REMINDER_WINDOW_END = time(11, 0)


@bp.route("/tasks/send-reminders", methods=["POST"])
def send_reminders():
    secret = current_app.config.get("CRON_SECRET")
    if not secret or request.headers.get("X-Cron-Secret") != secret:
        return jsonify({"error": "Forbidden"}), 403

    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    now_local = datetime.now(tz)

    if not (REMINDER_WINDOW_START <= now_local.time() < REMINDER_WINDOW_END):
        return jsonify(
            {"skipped": True, "reason": "outside reminder window", "local_time": now_local.isoformat()}
        )

    today_local = now_local.date()
    yesterday_local = today_local - timedelta(days=1)

    users = User.query.filter(User.email.isnot(None), User.email != "").all()
    sent = 0
    for user in users:
        if user.last_reminder_sent_date == today_local:
            continue
        send_reminder_email(
            current_app, user.email, yesterday_local.year, yesterday_local.month, yesterday_local.day
        )
        user.last_reminder_sent_date = today_local
        sent += 1

    db.session.commit()
    return jsonify({"success": True, "sent": sent, "local_time": now_local.isoformat()})

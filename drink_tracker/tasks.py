from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

from .mailer import send_reminder_email
from .models import User, db

bp = Blueprint("tasks", __name__)

# GitHub Actions' `schedule` trigger is best-effort and commonly delayed by
# 10-30+ minutes, especially under load, so an exact hour:minute match is too
# fragile — a delayed run just misses the one matching minute entirely. A
# window is caught by whichever hourly tick lands inside it, and per-user
# last_reminder_sent_date tracking still keeps it to once a day either way.
REMINDER_WINDOW_START = time(7, 30)
REMINDER_WINDOW_END = time(8, 30)


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

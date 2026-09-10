from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request

from .mailer import send_reminder_email
from .models import User, db

bp = Blueprint("tasks", __name__)

REMINDER_HOUR = 7
REMINDER_MINUTE = 35


@bp.route("/tasks/send-reminders", methods=["POST"])
def send_reminders():
    secret = current_app.config.get("CRON_SECRET")
    if not secret or request.headers.get("X-Cron-Secret") != secret:
        return jsonify({"error": "Forbidden"}), 403

    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    now_local = datetime.now(tz)

    if now_local.hour != REMINDER_HOUR or now_local.minute != REMINDER_MINUTE:
        return jsonify(
            {"skipped": True, "reason": "not reminder time local", "local_time": now_local.isoformat()}
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

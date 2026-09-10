from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app


def local_today():
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    return datetime.now(tz).date()

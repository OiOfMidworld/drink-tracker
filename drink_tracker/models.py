from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Color-coding bands used to display an exact drink count on the calendar.
CATEGORY_INFO = {
    0: {"label": "0", "color": "#2ecc71"},
    1: {"label": "1-3", "color": "#f1c40f"},
    2: {"label": "4-6", "color": "#9b59b6"},
    3: {"label": "7+", "color": "#111111"},
}


def category_for_count(count):
    if count <= 0:
        return 0
    if count <= 3:
        return 1
    if count <= 6:
        return 2
    return 3


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    entries = db.relationship(
        "Entry", backref="user", lazy=True, cascade="all, delete-orphan"
    )


class Entry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    drink_count = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "entry_date", name="uq_user_date"),
    )

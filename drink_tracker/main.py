import calendar as cal_module
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract

from .forms import SettingsForm
from .models import CATEGORY_INFO, Entry, category_for_count, db

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def index():
    today = date.today()
    return redirect(url_for("main.calendar_view", year=today.year, month=today.month))


@bp.route("/calendar/<int:year>/<int:month>")
@login_required
def calendar_view(year, month):
    if month < 1 or month > 12 or year < 1900 or year > 3000:
        abort(404)

    today = date.today()

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    calendar_obj = cal_module.Calendar(firstweekday=6)  # weeks start on Sunday
    weeks = calendar_obj.monthdayscalendar(year, month)

    days_in_month = cal_module.monthrange(year, month)[1]
    future_days = {d for d in range(1, days_in_month + 1) if date(year, month, d) > today}

    entries = Entry.query.filter(
        Entry.user_id == current_user.id,
        extract("year", Entry.entry_date) == year,
        extract("month", Entry.entry_date) == month,
    ).all()
    entry_map = {
        entry.entry_date.day: {
            "count": entry.drink_count,
            "category": category_for_count(entry.drink_count),
        }
        for entry in entries
    }

    weeks_with_totals = []
    for week in weeks:
        week_total = sum(entry_map[day]["count"] for day in week if day != 0 and day in entry_map)
        weeks_with_totals.append((week, week_total))

    # Only average over days that were actually logged — an unlogged day is unknown,
    # not a 0. (A future day can't be logged at all, so it's naturally excluded too.)
    logged_days_this_month = len(entry_map)
    total_month_drinks = sum(entry["count"] for entry in entry_map.values())
    avg_per_week = (
        (total_month_drinks / logged_days_this_month) * 7 if logged_days_this_month else 0
    )

    year_window_start = today - timedelta(days=364)
    yearly_total, logged_days_in_year = (
        db.session.query(
            db.func.coalesce(db.func.sum(Entry.drink_count), 0),
            db.func.count(Entry.id),
        )
        .filter(
            Entry.user_id == current_user.id,
            Entry.entry_date >= year_window_start,
            Entry.entry_date <= today,
        )
        .one()
    )
    yearly_avg_per_week = (yearly_total / logged_days_in_year) * 7 if logged_days_in_year else 0

    return render_template(
        "calendar.html",
        year=year,
        month=month,
        month_name=cal_module.month_name[month],
        weeks_with_totals=weeks_with_totals,
        avg_per_week=avg_per_week,
        yearly_avg_per_week=yearly_avg_per_week,
        entry_map=entry_map,
        future_days=future_days,
        category_info=CATEGORY_INFO,
        today=today,
        prev_year=prev_year,
        prev_month=prev_month,
        next_year=next_year,
        next_month=next_month,
    )


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        current_user.email = form.email.data or None
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("main.settings"))
    return render_template("settings.html", form=form)


@bp.route("/api/log", methods=["POST"])
@login_required
def log_day():
    data = request.get_json(silent=True) or {}
    date_str = data.get("date")
    count = data.get("count")

    try:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid date."}), 400

    if entry_date > date.today():
        return jsonify({"error": "You can't log a future date."}), 400

    entry = Entry.query.filter_by(user_id=current_user.id, entry_date=entry_date).first()

    if count is None:
        if entry:
            db.session.delete(entry)
            db.session.commit()
        return jsonify({"success": True, "count": None})

    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return jsonify({"error": "Enter a whole number of 0 or more."}), 400

    if entry:
        entry.drink_count = count
    else:
        entry = Entry(user_id=current_user.id, entry_date=entry_date, drink_count=count)
        db.session.add(entry)
    db.session.commit()

    category = category_for_count(count)
    return jsonify(
        {
            "success": True,
            "count": count,
            "category": category,
            "color": CATEGORY_INFO[category]["color"],
        }
    )

import os

from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from sqlalchemy import inspect, text

from .models import User, db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()

# db.create_all() only creates tables that don't exist yet — it never alters a table
# that's already there from an earlier deploy. This patches in columns added after a
# table already exists in production, without pulling in a full migration framework.
_USER_COLUMN_MIGRATIONS = {
    "email": 'ALTER TABLE "user" ADD COLUMN email VARCHAR(255)',
    "last_reminder_sent_date": 'ALTER TABLE "user" ADD COLUMN last_reminder_sent_date DATE',
}


def _add_missing_columns():
    inspector = inspect(db.engine)
    if "user" not in inspector.get_table_names():
        return
    existing_columns = {col["name"] for col in inspector.get_columns("user")}
    for column, ddl in _USER_COLUMN_MIGRATIONS.items():
        if column not in existing_columns:
            db.session.execute(text(ddl))
    db.session.commit()


def create_app():
    app = Flask(__name__, instance_relative_config=True)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    os.makedirs(app.instance_path, exist_ok=True)
    default_db_path = os.path.join(app.instance_path, "drinks.db")
    database_url = os.environ.get("DATABASE_URL", f"sqlite:///{default_db_path}")
    # Render (and Heroku) hand out "postgres://" URLs, but SQLAlchemy 1.4+ requires "postgresql://".
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # Render's Postgres (and most managed Postgres) closes idle connections server-side.
    # Without pre-ping, SQLAlchemy can hand out a pooled connection that's already been
    # dropped, surfacing as "SSL SYSCALL error: EOF detected" on the next query — pre-ping
    # tests each connection before use and transparently reconnects if it's gone stale.
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True, "pool_recycle": 280}

    app.config["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5050")
    app.config["APP_TIMEZONE"] = os.environ.get("APP_TIMEZONE", "America/New_York")
    app.config["CRON_SECRET"] = os.environ.get("CRON_SECRET", "")

    # Render blocks outbound SMTP on free web services, so reminder emails send via
    # Resend's HTTPS API instead of raw SMTP (see drink_tracker/mailer.py).
    app.config["RESEND_API_KEY"] = os.environ.get("RESEND_API_KEY")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", "onboarding@resend.dev")
    app.config["MAIL_SUPPRESS_SEND"] = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .tasks import bp as tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(tasks_bp)
    csrf.exempt(tasks_bp)

    with app.app_context():
        db.create_all()
        _add_missing_columns()

    return app

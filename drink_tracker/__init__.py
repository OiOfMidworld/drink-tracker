import os

from flask import Flask
from flask_login import LoginManager
from flask_wtf import CSRFProtect

from .mailer import mail
from .models import User, db

login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()


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

    app.config["APP_BASE_URL"] = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5050")
    app.config["APP_TIMEZONE"] = os.environ.get("APP_TIMEZONE", "America/New_York")
    app.config["CRON_SECRET"] = os.environ.get("CRON_SECRET", "")

    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
    app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER", app.config["MAIL_USERNAME"])
    app.config["MAIL_SUPPRESS_SEND"] = os.environ.get("MAIL_SUPPRESS_SEND", "false").lower() == "true"

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)

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

    return app

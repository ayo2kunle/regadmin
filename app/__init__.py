from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.events import events_bp
    from app.routes.main import main_bp
    from app.routes.registrations import registrations_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)

    with app.app_context():
        db.create_all()
        _ensure_admin_user(app)

    return app


def _ensure_admin_user(app):
    from app.models import User

    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]
    if not User.query.filter_by(username=username).first():
        admin = User(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

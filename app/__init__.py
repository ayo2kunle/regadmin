from flask import Flask, session
from flask_login import LoginManager, current_user
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

    from app.models import Tenant, TenantApplication, User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_tenant_context():
        context = {
            "platform_admin": False,
            "scope_tenants": [],
            "tenant_scope": "all",
            "pending_application_count": 0,
            "current_org": None,
            "viewing_org": None,
        }
        if not getattr(current_user, "is_authenticated", False):
            return context

        context["platform_admin"] = bool(current_user.is_platform_admin)
        if current_user.tenant:
            context["current_org"] = current_user.tenant.name
        if not context["platform_admin"]:
            context["viewing_org"] = context["current_org"]
            return context

        context["scope_tenants"] = Tenant.query.order_by(Tenant.name.asc()).all()
        scope = session.get("tenant_scope", "all")
        context["tenant_scope"] = scope
        context["pending_application_count"] = TenantApplication.query.filter_by(
            status=TenantApplication.STATUS_PENDING
        ).count()
        if scope not in (None, "all"):
            try:
                tenant = db.session.get(Tenant, int(scope))
            except (TypeError, ValueError):
                tenant = None
            context["viewing_org"] = tenant.name if tenant else None
        return context

    from app.routes.auth import auth_bp
    from app.routes.events import events_bp
    from app.routes.main import main_bp
    from app.routes.registrations import registrations_bp
    from app.routes.tenants import tenants_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(registrations_bp)
    app.register_blueprint(tenants_bp)

    with app.app_context():
        from app.bootstrap import prepare_database

        prepare_database(app)

    return app

from sqlalchemy import inspect, text

from app import db
from app.models import Event, Tenant, User

FOUNDING_TENANT_NAME = "RegAdmin"


def prepare_database(app):
    db.create_all()
    _add_missing_columns()
    _widen_username_column()
    founding = _ensure_founding_tenant()
    _backfill_existing_records(founding)
    _ensure_platform_admin(app, founding)


def _column_names(table_name):
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_missing_columns():
    is_postgres = db.engine.dialect.name == "postgresql"
    boolean = "BOOLEAN NOT NULL DEFAULT FALSE" if is_postgres else "BOOLEAN NOT NULL DEFAULT 0"
    additions = {
        "users": {
            "name": "name VARCHAR(120)",
            "email": "email VARCHAR(255)",
            "tenant_id": "tenant_id INTEGER",
            "is_platform_admin": f"is_platform_admin {boolean}",
            "is_tenant_admin": f"is_tenant_admin {boolean}",
        },
        "events": {
            "tenant_id": "tenant_id INTEGER",
        },
    }
    changed = False
    for table_name, columns in additions.items():
        existing = _column_names(table_name)
        for column_name, ddl in columns.items():
            if column_name not in existing:
                db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
                changed = True
    if changed:
        db.session.commit()
    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email_unique ON users (email)")
    )
    db.session.commit()


def _widen_username_column():
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(text("ALTER TABLE users ALTER COLUMN username TYPE VARCHAR(255)"))
    db.session.commit()


def _ensure_founding_tenant():
    founding = Tenant.query.filter_by(is_founding=True).first()
    if founding:
        return founding
    founding = Tenant(
        name=FOUNDING_TENANT_NAME,
        plan=Tenant.PLAN_STARTER,
        subscription_status="active",
        is_founding=True,
    )
    db.session.add(founding)
    db.session.commit()
    return founding


def _backfill_existing_records(founding):
    """Existing accounts are the first tenant and can administer every tenant."""
    User.query.filter(User.tenant_id.is_(None)).update(
        {
            User.tenant_id: founding.id,
            User.is_platform_admin: True,
            User.is_tenant_admin: True,
        },
        synchronize_session=False,
    )
    Event.query.filter(Event.tenant_id.is_(None)).update(
        {Event.tenant_id: founding.id},
        synchronize_session=False,
    )
    db.session.commit()


def _ensure_platform_admin(app, founding):
    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]
    admin = User.query.filter_by(username=username).first()
    if admin:
        admin.tenant_id = admin.tenant_id or founding.id
        admin.is_platform_admin = True
        admin.is_tenant_admin = True
        db.session.commit()
        return

    admin = User(
        username=username,
        name="Platform admin",
        tenant_id=founding.id,
        is_platform_admin=True,
        is_tenant_admin=True,
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

from sqlalchemy import inspect, text

from app import db
from app.models import Event, Tenant, User

FOUNDING_TENANT_NAME = "Jesus House Toronto"


def prepare_database(app):
    db.create_all()
    _add_missing_columns()
    _widen_username_column()
    founding = _ensure_founding_tenant()
    _assign_public_ids()
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
    boolean_on = "BOOLEAN NOT NULL DEFAULT TRUE" if is_postgres else "BOOLEAN NOT NULL DEFAULT 1"
    additions = {
        "users": {
            "name": "name VARCHAR(120)",
            "email": "email VARCHAR(255)",
            "tenant_id": "tenant_id INTEGER",
            "is_platform_admin": f"is_platform_admin {boolean}",
            "is_tenant_admin": f"is_tenant_admin {boolean}",
        },
        "tenants": {
            "public_id": "public_id VARCHAR(12)",
            "logo": "logo " + ("BYTEA" if is_postgres else "BLOB"),
            "logo_mime": "logo_mime VARCHAR(80)",
            "logo_in_header": f"logo_in_header {boolean_on}",
            "logo_on_public": f"logo_on_public {boolean_on}",
            "logo_on_qr": f"logo_on_qr {boolean_on}",
        },
        "events": {
            "tenant_id": "tenant_id INTEGER",
            "public_id": "public_id VARCHAR(12)",
            "field_config": "field_config TEXT",
            "cover_image": "cover_image " + ("BYTEA" if is_postgres else "BLOB"),
            "cover_mime": "cover_mime VARCHAR(80)",
            "cover_x": ("cover_x DOUBLE PRECISION NOT NULL DEFAULT 50" if is_postgres else "cover_x REAL NOT NULL DEFAULT 50"),
            "cover_y": ("cover_y DOUBLE PRECISION NOT NULL DEFAULT 50" if is_postgres else "cover_y REAL NOT NULL DEFAULT 50"),
            "cover_scale": ("cover_scale DOUBLE PRECISION NOT NULL DEFAULT 1" if is_postgres else "cover_scale REAL NOT NULL DEFAULT 1"),
            "address_id": "address_id INTEGER",
        },
        "registrations": {
            "custom_data": "custom_data TEXT",
            "self_registered": f"self_registered {boolean}",
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
    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_tenants_public_id ON tenants (public_id)")
    )
    db.session.execute(
        text("CREATE UNIQUE INDEX IF NOT EXISTS ix_events_public_id ON events (public_id)")
    )
    db.session.commit()


def _widen_username_column():
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(text("ALTER TABLE users ALTER COLUMN username TYPE VARCHAR(255)"))
    db.session.commit()


def _assign_public_ids():
    from app.codes import assign_public_id

    changed = False
    for tenant in Tenant.query.filter(Tenant.public_id.is_(None)).all():
        assign_public_id(tenant)
        db.session.flush()
        changed = True
    for event in Event.query.filter(Event.public_id.is_(None)).all():
        assign_public_id(event)
        db.session.flush()
        changed = True
    if changed:
        db.session.commit()


def _ensure_founding_tenant():
    founding = Tenant.query.filter_by(is_founding=True).first()
    if founding:
        if founding.name != FOUNDING_TENANT_NAME:
            founding.name = FOUNDING_TENANT_NAME
            db.session.commit()
        return founding
    founding = Tenant(
        name=FOUNDING_TENANT_NAME,
        plan=Tenant.PLAN_STARTER,
        subscription_status="active",
        is_founding=True,
    )
    from app.codes import assign_public_id

    assign_public_id(founding)
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

from functools import wraps

from flask import abort, flash, redirect, session, url_for
from flask_login import current_user

from app.models import Event, Registration

ALL_TENANTS = "all"


def platform_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request_path()))
        if not current_user.is_platform_admin:
            flash("Only a platform admin can do that.", "error")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def tenant_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request_path()))
        if not current_user.is_tenant_admin or current_user.tenant is None:
            flash("Only an organization admin can do that.", "error")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def request_path():
    from flask import request

    return request.path


def tenant_scope():
    """None means every tenant. Regular users are always locked to their own."""
    if not current_user.is_authenticated:
        return None
    if not current_user.is_platform_admin:
        return current_user.tenant_id
    scope = session.get("tenant_scope", ALL_TENANTS)
    if scope in (None, ALL_TENANTS, "all"):
        return None
    from app.models import Tenant

    tenant = Tenant.query.filter_by(public_id=str(scope)).first()
    if tenant is None and str(scope).isdigit():
        tenant = db_get_tenant(int(scope))
    return tenant.id if tenant else None


def db_get_tenant(tenant_id):
    from app import db
    from app.models import Tenant

    return db.session.get(Tenant, tenant_id)


def events_query():
    query = Event.query
    tenant_id = tenant_scope()
    if tenant_id:
        query = query.filter(Event.tenant_id == tenant_id)
    elif not current_user.is_platform_admin:
        query = query.filter(Event.tenant_id == current_user.tenant_id)
    return query


def registrations_query():
    query = Registration.query.join(Event)
    tenant_id = tenant_scope()
    if tenant_id:
        query = query.filter(Event.tenant_id == tenant_id)
    elif not current_user.is_platform_admin:
        query = query.filter(Event.tenant_id == current_user.tenant_id)
    return query


def get_accessible_event(code):
    event = events_query().filter(Event.public_id == str(code)).first()
    if event is None:
        abort(404)
    return event


def tenant_for_new_record():
    scoped = tenant_scope()
    if scoped:
        return scoped
    return current_user.tenant_id

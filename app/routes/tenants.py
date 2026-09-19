from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from app import db
from app.models import Tenant, TenantApplication, User
from app.tenancy import ALL_TENANTS, platform_admin_required

tenants_bp = Blueprint("tenants", __name__, url_prefix="/tenants")


@tenants_bp.route("/")
@platform_admin_required
def index():
    pending = (
        TenantApplication.query.filter_by(status=TenantApplication.STATUS_PENDING)
        .order_by(TenantApplication.created_at.asc())
        .all()
    )
    rejected = (
        TenantApplication.query.filter_by(status=TenantApplication.STATUS_REJECTED)
        .order_by(TenantApplication.reviewed_at.desc())
        .limit(10)
        .all()
    )
    tenants = Tenant.query.order_by(Tenant.created_at.asc()).all()
    return render_template(
        "tenants/index.html",
        pending=pending,
        rejected=rejected,
        tenants=tenants,
    )


@tenants_bp.route("/applications/<int:application_id>/approve", methods=["POST"])
@platform_admin_required
def approve(application_id):
    application = TenantApplication.query.get_or_404(application_id)
    if application.status != TenantApplication.STATUS_PENDING:
        flash("That request has already been reviewed.", "warning")
        return redirect(url_for("tenants.index"))

    if User.query.filter(db.func.lower(User.email) == application.email).first():
        flash("An account with that email already exists.", "error")
        return redirect(url_for("tenants.index"))
    if User.query.filter_by(username=application.email).first():
        flash("An account with that email already exists.", "error")
        return redirect(url_for("tenants.index"))

    tenant = Tenant(
        name=application.organization_name,
        plan=Tenant.PLAN_STARTER,
        subscription_status="active",
        is_founding=False,
    )
    db.session.add(tenant)
    db.session.flush()

    user = User(
        username=application.email,
        name=application.applicant_name,
        email=application.email,
        password_hash=application.password_hash,
        tenant_id=tenant.id,
        is_platform_admin=False,
        is_tenant_admin=True,
    )
    application.status = TenantApplication.STATUS_APPROVED
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewed_by_id = current_user.id
    db.session.add(user)
    db.session.commit()
    flash(
        f'Approved {application.organization_name}. Their tenant is active and they can sign in.',
        "success",
    )
    return redirect(url_for("tenants.index"))


@tenants_bp.route("/applications/<int:application_id>/reject", methods=["POST"])
@platform_admin_required
def reject(application_id):
    application = TenantApplication.query.get_or_404(application_id)
    if application.status != TenantApplication.STATUS_PENDING:
        flash("That request has already been reviewed.", "warning")
        return redirect(url_for("tenants.index"))

    application.status = TenantApplication.STATUS_REJECTED
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewed_by_id = current_user.id
    db.session.commit()
    flash(f"Declined the request from {application.organization_name}.", "success")
    return redirect(url_for("tenants.index"))


@tenants_bp.route("/scope", methods=["POST"])
@platform_admin_required
def set_scope():
    value = (request.form.get("tenant_scope") or ALL_TENANTS).strip()
    if value == ALL_TENANTS:
        session["tenant_scope"] = ALL_TENANTS
    else:
        tenant = Tenant.query.get(int(value))
        if tenant is None:
            flash("That organization was not found.", "error")
        else:
            session["tenant_scope"] = tenant.id
    return redirect(request.referrer or url_for("main.dashboard"))

import io
from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user

from app import db
from app.models import Tenant, TenantApplication, User
from app.tenancy import ALL_TENANTS, platform_admin_required, tenant_admin_required

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
    from app.codes import assign_public_id

    assign_public_id(tenant)
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
        tenant = Tenant.query.filter_by(public_id=value).first()
        if tenant is None:
            flash("That organization was not found.", "error")
        else:
            session["tenant_scope"] = tenant.public_id
    return redirect(request.referrer or url_for("main.dashboard"))


MAX_LOGO_BYTES = 2 * 1024 * 1024


def _read_logo():
    uploaded = request.files.get("logo")
    if uploaded is None or not uploaded.filename:
        return None, None, None
    data = uploaded.read()
    if not data:
        return None, None, None
    if len(data) > MAX_LOGO_BYTES:
        return None, None, "Logo must be 2 MB or smaller."
    if data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        mime = "image/gif"
    elif len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        return None, None, "Use a JPG, PNG, WebP, or GIF logo."
    return data, mime, None


@tenants_bp.route("/settings", methods=["GET", "POST"])
@tenant_admin_required
def settings():
    tenant = current_user.tenant
    if request.method == "POST":
        logo, mime, logo_error = _read_logo()
        if logo_error:
            flash(logo_error, "error")
            return redirect(url_for("tenants.settings"))
        if logo:
            tenant.logo = logo
            tenant.logo_mime = mime
        elif request.form.get("remove_logo") == "1":
            tenant.logo = None
            tenant.logo_mime = None
        tenant.logo_in_header = request.form.get("logo_in_header") == "1"
        tenant.logo_on_public = request.form.get("logo_on_public") == "1"
        tenant.logo_on_qr = request.form.get("logo_on_qr") == "1"
        db.session.commit()
        flash("Organization settings saved.", "success")
        return redirect(url_for("tenants.settings"))
    return render_template("tenants/settings.html", tenant=tenant)


@tenants_bp.route("/<public_id>/logo")
def logo(public_id):
    tenant = Tenant.query.filter_by(public_id=public_id).first_or_404()
    if not tenant.logo:
        abort(404)
    return send_file(
        io.BytesIO(tenant.logo),
        mimetype=tenant.logo_mime or "image/png",
        max_age=3600,
    )

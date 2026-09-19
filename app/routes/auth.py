import io
import re

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash

from app import db
from app.captcha import captcha_matches, clear_captcha, current_code, issue_captcha, render_captcha
from app.models import Tenant, TenantApplication, User
from app.tenancy import platform_admin_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def valid_email(value: str) -> bool:
    return bool(_EMAIL.match(value))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        login_id = (request.form.get("login") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter(db.func.lower(User.email) == login_id.lower()).first()
        if user is None:
            user = User.query.filter_by(username=login_id).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            flash("Signed in successfully.", "success")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = {
        "name": "",
        "email": "",
        "organization_name": "",
    }
    if request.method == "POST":
        form["name"] = (request.form.get("name") or "").strip()
        form["email"] = (request.form.get("email") or "").strip().lower()
        form["organization_name"] = (request.form.get("organization_name") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if not form["name"]:
            errors.append("Name is required.")
        if not valid_email(form["email"]):
            errors.append("Enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        elif password != confirm:
            errors.append("Passwords do not match.")
        if not form["organization_name"]:
            errors.append("Organization name is required.")
        if current_code() is None:
            errors.append("The verification image expired. Enter the characters in the new image.")
        elif not captcha_matches(request.form.get("captcha") or ""):
            errors.append("The characters did not match the image.")

        if form["email"] and not errors:
            if User.query.filter(db.func.lower(User.email) == form["email"]).first():
                errors.append("That email already belongs to an account.")
            elif User.query.filter_by(username=form["email"]).first():
                errors.append("That email already belongs to an account.")
            elif TenantApplication.query.filter_by(
                email=form["email"], status=TenantApplication.STATUS_PENDING
            ).first():
                errors.append("That email already has a request waiting for approval.")

        if errors:
            for message in errors:
                flash(message, "error")
        else:
            application = TenantApplication(
                applicant_name=form["name"],
                email=form["email"],
                password_hash=generate_password_hash(password),
                organization_name=form["organization_name"],
                status=TenantApplication.STATUS_PENDING,
            )
            db.session.add(application)
            db.session.commit()
            clear_captcha()
            return redirect(url_for("auth.register_submitted", email=form["email"]))

    captcha_id = issue_captcha()
    return render_template("auth/register.html", form=form, captcha_id=captcha_id)


@auth_bp.route("/captcha.png")
def captcha_image():
    if request.args.get("refresh") or current_code() is None:
        issue_captcha()
    code = current_code()
    response = send_file(io.BytesIO(render_captcha(code)), mimetype="image/png")
    response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


@auth_bp.route("/register/submitted")
def register_submitted():
    email = (request.args.get("email") or "").strip()
    return render_template("auth/register_submitted.html", email=email)


@auth_bp.route("/admins")
@platform_admin_required
def list_admins():
    admins = (
        User.query.filter_by(is_platform_admin=True).order_by(User.created_at.asc()).all()
    )
    return render_template("auth/admins.html", admins=admins)


@auth_bp.route("/admins/new", methods=["GET", "POST"])
@platform_admin_required
def create_admin():
    """Platform admins can add another admin with access to every tenant."""
    founding = Tenant.query.filter_by(is_founding=True).first()
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        if not username or not password:
            flash("Username and password are required.", "error")
        elif len(username) < 3:
            flash("Username must be at least 3 characters.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(username=username).first():
            flash("That username is already taken.", "error")
        else:
            user = User(
                username=username,
                name=username,
                tenant_id=founding.id if founding else current_user.tenant_id,
                is_platform_admin=True,
                is_tenant_admin=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f'Admin "{username}" created.', "success")
            return redirect(url_for("auth.list_admins"))

    return render_template("auth/create_admin.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "success")
    return redirect(url_for("auth.login"))

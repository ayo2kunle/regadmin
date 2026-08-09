from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Event, Registration

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    upcoming_events = (
        Event.query.order_by(Event.event_date.asc()).limit(5).all()
    )
    recent_registrations = (
        Registration.query.order_by(Registration.created_at.desc()).limit(8).all()
    )
    stats = {
        "events": Event.query.count(),
        "registrations": Registration.query.count(),
        "new_members": Registration.query.filter_by(
            member_type=Registration.MEMBER_NEW
        ).count(),
        "existing_members": Registration.query.filter_by(
            member_type=Registration.MEMBER_EXISTING
        ).count(),
    }
    return render_template(
        "main/dashboard.html",
        upcoming_events=upcoming_events,
        recent_registrations=recent_registrations,
        stats=stats,
    )

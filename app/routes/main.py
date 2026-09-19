from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.models import Event, Registration
from app.tenancy import events_query, registrations_query

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("main/index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    upcoming_events = events_query().order_by(Event.event_date.asc()).limit(5).all()
    recent_registrations = (
        registrations_query().order_by(Registration.created_at.desc()).limit(8).all()
    )
    scoped_registrations = registrations_query()
    stats = {
        "events": events_query().count(),
        "registrations": scoped_registrations.count(),
        "new_members": scoped_registrations.filter(
            Registration.member_type == Registration.MEMBER_NEW
        ).count(),
        "existing_members": scoped_registrations.filter(
            Registration.member_type == Registration.MEMBER_EXISTING
        ).count(),
    }
    return render_template(
        "main/dashboard.html",
        upcoming_events=upcoming_events,
        recent_registrations=recent_registrations,
        stats=stats,
    )

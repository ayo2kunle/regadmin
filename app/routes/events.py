from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import db
from app.exports import build_event_registrations_workbook, event_export_filename
from app.models import Event, Registration

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
@login_required
def list_events():
    events = Event.query.order_by(Event.event_date.desc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        venue = (request.form.get("venue") or "").strip()
        description = (request.form.get("description") or "").strip()
        date_raw = (request.form.get("event_date") or "").strip()

        errors = []
        if not name:
            errors.append("Event name is required.")
        if not venue:
            errors.append("Venue is required.")
        event_date = None
        if not date_raw:
            errors.append("Event date is required.")
        else:
            try:
                event_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
            except ValueError:
                errors.append("Use a valid date (YYYY-MM-DD).")

        if errors:
            for message in errors:
                flash(message, "error")
        else:
            event = Event(
                name=name,
                venue=venue,
                description=description or None,
                event_date=event_date,
                created_by_id=current_user.id,
            )
            db.session.add(event)
            db.session.commit()
            flash(f'Event "{event.name}" created.', "success")
            return redirect(url_for("events.detail", event_id=event.id))

    return render_template("events/form.html", event=None)


@events_bp.route("/<int:event_id>")
@login_required
def detail(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = event.registrations.order_by(Registration.created_at.desc()).all()
    return render_template(
        "events/detail.html", event=event, registrations=registrations
    )


@events_bp.route("/<int:event_id>/export.xlsx")
@login_required
def export_registrations(event_id):
    event = Event.query.get_or_404(event_id)
    registrations = event.registrations.order_by(
        Registration.last_name.asc(), Registration.first_name.asc()
    ).all()
    workbook = build_event_registrations_workbook(event, registrations)
    return send_file(
        workbook,
        as_attachment=True,
        download_name=event_export_filename(event),
        mimetype=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )

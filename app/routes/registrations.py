from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.fields import collect_registration, visible_columns
from app.models import Event, Registration
from app.tenancy import events_query, get_accessible_event, registrations_query

registrations_bp = Blueprint("registrations", __name__, url_prefix="/registrations")


@registrations_bp.route("/")
@login_required
def list_registrations():
    event_id = request.args.get("event_id", type=int)
    member_type = request.args.get("member_type", "").strip()

    query = registrations_query()
    if event_id:
        query = query.filter(Registration.event_id == event_id)
    if member_type in Registration.MEMBER_TYPES:
        query = query.filter(Registration.member_type == member_type)

    registrations = query.order_by(Registration.created_at.desc()).all()
    events = events_query().order_by(Event.event_date.desc()).all()
    column_event = None
    columns = []
    if event_id:
        column_event = next((event for event in events if event.id == event_id), None)
        if column_event:
            columns = visible_columns(column_event.settings)
    return render_template(
        "registrations/list.html",
        registrations=registrations,
        events=events,
        selected_event_id=event_id,
        selected_member_type=member_type,
        column_event=column_event,
        columns=columns,
    )


@registrations_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_registration():
    events = events_query().order_by(Event.event_date.asc()).all()
    preselected_event_id = request.args.get("event_id", type=int)

    if request.method == "POST":
        event_id = request.form.get("event_id", type=int)
        event = events_query().filter_by(id=event_id).first() if event_id else None
        errors = []
        values = None
        if not event:
            errors.append("Select an event.")
        else:
            errors, values = collect_registration(event, request.form)
            if values["email"]:
                duplicate = Registration.query.filter_by(
                    event_id=event.id, email=values["email"]
                ).first()
                if duplicate:
                    errors.append("This email is already registered for that event.")

        if errors:
            for message in errors:
                flash(message, "error")
            preselected_event_id = event_id
        else:
            registration = Registration(
                event_id=event.id,
                registered_by_id=current_user.id,
                self_registered=False,
                **values,
            )
            db.session.add(registration)
            db.session.commit()
            flash(f"{registration.full_name} registered for {event.name}.", "success")
            return redirect(url_for("events.detail", event_id=event.id))

    active_event = None
    if preselected_event_id:
        active_event = events_query().filter_by(id=preselected_event_id).first()

    return render_template(
        "registrations/form.html",
        events=events,
        preselected_event_id=preselected_event_id,
        active_event=active_event,
        settings=active_event.settings if active_event else None,
    )


@registrations_bp.route("/<int:registration_id>")
@login_required
def detail(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    get_accessible_event(registration.event_id)
    return render_template("registrations/detail.html", registration=registration)

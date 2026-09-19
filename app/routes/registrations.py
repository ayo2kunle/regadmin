from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
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
    return render_template(
        "registrations/list.html",
        registrations=registrations,
        events=events,
        selected_event_id=event_id,
        selected_member_type=member_type,
    )


@registrations_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_registration():
    events = events_query().order_by(Event.event_date.asc()).all()
    preselected_event_id = request.args.get("event_id", type=int)

    if request.method == "POST":
        event_id = request.form.get("event_id", type=int)
        first_name = (request.form.get("first_name") or "").strip()
        last_name = (request.form.get("last_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        member_type = (request.form.get("member_type") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        errors = []
        event = events_query().filter_by(id=event_id).first() if event_id else None
        if not event:
            errors.append("Select an event.")
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if member_type not in Registration.MEMBER_TYPES:
            errors.append("Select whether this is an existing or new member.")

        if event and email:
            duplicate = Registration.query.filter_by(
                event_id=event.id, email=email
            ).first()
            if duplicate:
                errors.append("This email is already registered for that event.")

        if errors:
            for message in errors:
                flash(message, "error")
        else:
            registration = Registration(
                event_id=event.id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone or None,
                member_type=member_type,
                notes=notes or None,
                registered_by_id=current_user.id,
            )
            db.session.add(registration)
            db.session.commit()
            flash(
                f"{registration.full_name} registered for {event.name} "
                f"({registration.member_type_label}).",
                "success",
            )
            return redirect(url_for("events.detail", event_id=event.id))

    return render_template(
        "registrations/form.html",
        events=events,
        preselected_event_id=preselected_event_id,
        registration=None,
    )


@registrations_bp.route("/<int:registration_id>")
@login_required
def detail(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    get_accessible_event(registration.event_id)
    return render_template("registrations/detail.html", registration=registration)

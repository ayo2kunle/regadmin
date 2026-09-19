import io
from datetime import datetime

import qrcode
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.exports import build_event_registrations_workbook, event_export_filename
from app.fields import collect_registration, custom_slots, dump_settings, settings_from_form, visible_columns
from app.models import Event, Registration, Tenant
from app.tenancy import events_query, get_accessible_event, tenant_for_new_record

events_bp = Blueprint("events", __name__, url_prefix="/events")

MAX_COVER_BYTES = 3 * 1024 * 1024


def _sniff_image(data: bytes):
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) > 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _clamp(value, low, high, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


def _apply_cover(event):
    uploaded = request.files.get("cover")
    if uploaded and uploaded.filename:
        data = uploaded.read()
        if len(data) > MAX_COVER_BYTES:
            return "Image must be 3 MB or smaller."
        mime = _sniff_image(data)
        if not mime:
            return "Use a JPG, PNG, WebP, or GIF image."
        event.cover_image = data
        event.cover_mime = mime
    elif request.form.get("remove_cover") == "1":
        event.cover_image = None
        event.cover_mime = None

    event.cover_x = _clamp(request.form.get("cover_x"), 0, 100, 50)
    event.cover_y = _clamp(request.form.get("cover_y"), 0, 100, 50)
    event.cover_scale = _clamp(request.form.get("cover_scale"), 1, 3, 1)
    return None


def _event_form_context(event):
    tenants = []
    selected_tenant_id = current_user.tenant_id
    if current_user.is_platform_admin:
        tenants = Tenant.query.order_by(Tenant.name.asc()).all()
        selected_tenant_id = event.tenant_id if event else tenant_for_new_record()
    settings = event.settings if event else None
    from app.fields import default_settings

    if request.method == "POST":
        active_settings = settings_from_form(request.form)
    else:
        active_settings = settings or default_settings()
    return {
        "event": event,
        "tenants": tenants,
        "selected_tenant_id": selected_tenant_id,
        "settings": active_settings,
        "custom_slots": custom_slots(active_settings),
    }


def _read_event_basics():
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

    tenant_id = current_user.tenant_id
    if current_user.is_platform_admin:
        tenant_id = request.form.get("tenant_id", type=int) or tenant_for_new_record()
        if not tenant_id or not db.session.get(Tenant, tenant_id):
            errors.append("Select an organization.")
    return errors, {
        "name": name,
        "venue": venue,
        "description": description or None,
        "event_date": event_date,
        "tenant_id": tenant_id,
    }


@events_bp.route("/")
@login_required
def list_events():
    events = events_query().order_by(Event.event_date.desc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        errors, basics = _read_event_basics()
        event = Event(
            name=basics["name"] or "Untitled",
            venue=basics["venue"] or "TBD",
            description=basics["description"],
            event_date=basics["event_date"] or datetime.utcnow().date(),
            created_by_id=current_user.id,
            tenant_id=basics["tenant_id"],
            field_config=dump_settings(settings_from_form(request.form)),
        )
        cover_error = _apply_cover(event)
        if cover_error:
            errors.append(cover_error)
        if errors or not basics["event_date"]:
            for message in errors:
                flash(message, "error")
        else:
            event.name = basics["name"]
            event.venue = basics["venue"]
            db.session.add(event)
            db.session.commit()
            flash(f'Event "{event.name}" created.', "success")
            return redirect(url_for("events.detail", event_id=event.id))

    return render_template("events/form.html", **_event_form_context(None))


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = get_accessible_event(event_id)
    if request.method == "POST":
        errors, basics = _read_event_basics()
        cover_error = _apply_cover(event)
        if cover_error:
            errors.append(cover_error)
        if errors or not basics["event_date"]:
            for message in errors:
                flash(message, "error")
        else:
            event.name = basics["name"]
            event.venue = basics["venue"]
            event.description = basics["description"]
            event.event_date = basics["event_date"]
            event.tenant_id = basics["tenant_id"]
            event.field_config = dump_settings(settings_from_form(request.form))
            db.session.commit()
            flash("Event updated.", "success")
            return redirect(url_for("events.detail", event_id=event.id))
    return render_template("events/form.html", **_event_form_context(event))


@events_bp.route("/<int:event_id>")
@login_required
def detail(event_id):
    event = get_accessible_event(event_id)
    registrations = event.registrations.order_by(Registration.created_at.desc()).all()
    columns = visible_columns(event.settings)
    join_url = url_for("events.public_register", event_id=event.id, _external=True)
    return render_template(
        "events/detail.html",
        event=event,
        registrations=registrations,
        columns=columns,
        join_url=join_url,
    )


@events_bp.route("/<int:event_id>/cover")
def cover(event_id):
    event = db.session.get(Event, event_id)
    if event is None or not event.cover_image:
        return ("", 404)
    return send_file(
        io.BytesIO(event.cover_image),
        mimetype=event.cover_mime or "image/jpeg",
        max_age=3600,
    )


@events_bp.route("/<int:event_id>/qr.png")
@login_required
def qr_code(event_id):
    event = get_accessible_event(event_id)
    join_url = url_for("events.public_register", event_id=event.id, _external=True)
    image = qrcode.make(join_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    download = request.args.get("download") == "1"
    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=download,
        download_name=f"{event.name}-registration-qr.png",
    )


@events_bp.route("/<int:event_id>/register", methods=["GET", "POST"])
def public_register(event_id):
    event = db.session.get(Event, event_id)
    if event is None:
        return render_template("events/public_missing.html"), 404

    if request.method == "POST":
        errors, values = collect_registration(event, request.form)
        if values["email"]:
            duplicate = Registration.query.filter_by(
                event_id=event.id, email=values["email"]
            ).first()
            if duplicate:
                errors.append("This email is already registered for this event.")
        if errors:
            for message in errors:
                flash(message, "error")
        else:
            registration = Registration(
                event_id=event.id,
                registered_by_id=event.created_by_id,
                self_registered=True,
                **values,
            )
            db.session.add(registration)
            db.session.commit()
            return render_template("events/public_thanks.html", event=event)

    return render_template(
        "events/public_register.html",
        event=event,
        settings=event.settings,
    )


@events_bp.route("/<int:event_id>/export.xlsx")
@login_required
def export_registrations(event_id):
    event = get_accessible_event(event_id)
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

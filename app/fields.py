import json
import re

BUILTIN_FIELDS = (
    ("email", "Email"),
    ("phone", "Phone"),
    ("member_type", "Member type"),
    ("notes", "Notes"),
)

MAX_CUSTOM_FIELDS = 5
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def default_settings():
    return {
        "builtin": {
            key: {"label": label, "visible": True, "required": False}
            for key, label in BUILTIN_FIELDS
        },
        "custom": [],
    }


def parse_stored_config(raw):
    settings = default_settings()
    if not raw:
        return settings
    try:
        stored = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return settings

    builtin = stored.get("builtin") or {}
    for key, label in BUILTIN_FIELDS:
        item = builtin.get(key) or {}
        settings["builtin"][key] = {
            "label": label,
            "visible": bool(item.get("visible", True)),
            "required": bool(item.get("required", False)) and bool(item.get("visible", True)),
        }

    custom = []
    allowed_keys = {f"c{number}" for number in range(1, MAX_CUSTOM_FIELDS + 1)}
    for index, item in enumerate(stored.get("custom") or []):
        if len(custom) >= MAX_CUSTOM_FIELDS:
            break
        label = (item.get("label") or "").strip()
        if not label:
            continue
        key = item.get("key") if item.get("key") in allowed_keys else f"c{index + 1}"
        visible = bool(item.get("visible", True))
        custom.append(
            {
                "key": key,
                "label": label[:80],
                "visible": visible,
                "required": bool(item.get("required", False)) and visible,
            }
        )
    settings["custom"] = custom
    return settings


def custom_slots(settings):
    slots = []
    for index in range(MAX_CUSTOM_FIELDS):
        key = f"c{index + 1}"
        existing = next((item for item in settings["custom"] if item["key"] == key), None)
        slots.append(
            existing
            or {"key": key, "label": "", "visible": True, "required": False}
        )
    return slots


def settings_from_form(form):
    settings = default_settings()
    for key, label in BUILTIN_FIELDS:
        visible = form.get(f"show_{key}") == "1"
        required = visible and form.get(f"require_{key}") == "1"
        settings["builtin"][key] = {
            "label": label,
            "visible": visible,
            "required": required,
        }

    custom = []
    for index in range(MAX_CUSTOM_FIELDS):
        label = (form.get(f"custom_label_{index}") or "").strip()
        if not label:
            continue
        visible = form.get(f"custom_show_{index}") == "1"
        custom.append(
            {
                "key": f"c{index + 1}",
                "label": label[:80],
                "visible": visible,
                "required": visible and form.get(f"custom_require_{index}") == "1",
            }
        )
    settings["custom"] = custom
    return settings


def dump_settings(settings) -> str:
    return json.dumps(settings)


def visible_columns(settings):
    columns = [("first_name", "First name"), ("last_name", "Last name")]
    for key, spec in settings["builtin"].items():
        if spec["visible"]:
            columns.append((key, spec["label"]))
    for field in settings["custom"]:
        if field["visible"]:
            columns.append((field["key"], field["label"]))
    return columns


def collect_registration(event, form):
    settings = event.settings
    errors = []
    first_name = (form.get("first_name") or "").strip()
    last_name = (form.get("last_name") or "").strip()
    if not first_name:
        errors.append("First name is required.")
    if not last_name:
        errors.append("Last name is required.")

    email = ""
    phone = ""
    member_type = ""
    notes = ""
    email_spec = settings["builtin"]["email"]
    if email_spec["visible"]:
        email = (form.get("email") or "").strip().lower()
        if email_spec["required"] and not email:
            errors.append("Email is required.")
        elif email and not _EMAIL.match(email):
            errors.append("Enter a valid email address.")
    phone_spec = settings["builtin"]["phone"]
    if phone_spec["visible"]:
        phone = (form.get("phone") or "").strip()
        if phone_spec["required"] and not phone:
            errors.append("Phone is required.")
    member_spec = settings["builtin"]["member_type"]
    if member_spec["visible"]:
        member_type = (form.get("member_type") or "").strip()
        if member_type not in ("existing", "new"):
            if member_spec["required"]:
                errors.append("Select whether this is an existing or new member.")
            member_type = ""
    notes_spec = settings["builtin"]["notes"]
    if notes_spec["visible"]:
        notes = (form.get("notes") or "").strip()
        if notes_spec["required"] and not notes:
            errors.append("Notes are required.")

    custom = {}
    for field in settings["custom"]:
        if not field["visible"]:
            continue
        value = (form.get(f"custom_{field['key']}") or "").strip()
        if field["required"] and not value:
            errors.append(f"{field['label']} is required.")
        custom[field["key"]] = value[:500]

    values = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone or None,
        "member_type": member_type,
        "notes": notes or None,
        "custom_data": json.dumps(custom) if custom else None,
    }
    return errors, values

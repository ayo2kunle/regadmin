import re
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip()
    cleaned = re.sub(r"[-\s]+", "-", cleaned)
    return cleaned[:80] or "event"


def build_event_registrations_workbook(event, registrations) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Registrations"

    headers = [
        "First name",
        "Last name",
        "Email",
        "Phone",
        "Member type",
        "Notes",
        "Registered by",
        "Registered at (UTC)",
        "Event",
        "Event date",
        "Venue",
    ]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    for reg in registrations:
        sheet.append(
            [
                reg.first_name,
                reg.last_name,
                reg.email,
                reg.phone or "",
                reg.member_type_label,
                reg.notes or "",
                reg.registered_by_user.username,
                reg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                event.name,
                event.event_date.strftime("%Y-%m-%d"),
                event.venue,
            ]
        )

    widths = [16, 16, 28, 16, 16, 30, 16, 22, 24, 14, 24]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def event_export_filename(event) -> str:
    date_part = event.event_date.strftime("%Y-%m-%d")
    return f"{_safe_filename(event.name)}-{date_part}-registrations.xlsx"

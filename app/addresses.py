from app.models import Address
from app.places import find_country


def read_new_address(form, tenant_id):
    """Build an unsaved Address from the quick-add fields. Returns errors and the record."""
    street = (form.get("street") or "").strip()
    city = (form.get("city") or "").strip()
    postal_code = (form.get("postal_code") or "").strip()
    country_code = (form.get("country_code") or "").strip().upper()
    state_code = (form.get("state_code") or "").strip()
    state_free = (form.get("state_name") or "").strip()

    errors = []
    if not street:
        errors.append("Street is required.")
    if len(street) > 200:
        errors.append("Street is too long.")
    if len(city) > 120:
        errors.append("City is too long.")
    if len(postal_code) > 20:
        errors.append("Postal code is too long.")

    try:
        country = find_country(country_code) if country_code else None
    except Exception:
        return ["The country list is unavailable. Try again in a moment."], None
    if not country_code:
        errors.append("Country is required.")
    elif country is None:
        errors.append("Choose a country from the list.")

    state_name = ""
    stored_code = ""
    if country:
        if country["states"]:
            match = next((state for state in country["states"] if state["code"] == state_code), None)
            if match is None:
                errors.append("Choose a state or province.")
            else:
                state_name = match["name"]
                stored_code = match["code"]
        else:
            state_name = state_free
            stored_code = ""

    address = Address(
        tenant_id=tenant_id,
        street=street or "Unknown",
        city=city,
        state_code=stored_code,
        state_name=state_name,
        country_code=country["code"] if country else country_code[:2],
        country_name=country["name"] if country else "",
        postal_code=postal_code,
    )
    if errors:
        return errors, None
    return [], address

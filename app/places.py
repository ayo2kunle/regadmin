"""Country, state, and postal-code hints from public address directories."""

import json
import threading
import urllib.request

COUNTRIES_URL = "https://countriesnow.space/api/v0.1/countries/states"
POSTAL_URL = "https://chromium-i18n.appspot.com/ssl-address/data/{code}"

_lock = threading.Lock()
_countries = None
_postal = {}


def list_countries():
    global _countries
    with _lock:
        if _countries is None:
            _countries = _download_countries()
        return _countries


def country_places(code: str):
    code = (code or "").strip().upper()
    match = next((country for country in list_countries() if country["code"] == code), None)
    if match is None:
        return None
    postal = _postal_hints(code)
    prefixes = postal.get("prefixes") or {}
    return {
        "code": match["code"],
        "name": match["name"],
        "states": match["states"],
        "postal_examples": postal.get("examples") or [],
        "postal_prefixes": {state["code"]: prefixes.get(state["code"], "") for state in match["states"] if prefixes.get(state["code"])},
    }


def find_country(code: str):
    code = (code or "").strip().upper()
    return next((country for country in list_countries() if country["code"] == code), None)


def _download_countries():
    payload = _get_json(COUNTRIES_URL)
    rows = payload.get("data") or []
    countries = []
    for row in rows:
        code = (row.get("iso2") or "").strip().upper()
        name = (row.get("name") or "").strip()
        if len(code) != 2 or not name:
            continue
        states = []
        seen = set()
        for state in row.get("states") or []:
            state_name = (state.get("name") or "").strip()
            state_code = (state.get("state_code") or "").strip() or state_name
            if not state_name or state_code in seen:
                continue
            seen.add(state_code)
            states.append({"code": state_code, "name": state_name})
        states.sort(key=lambda item: item["name"].casefold())
        countries.append({"code": code, "name": name, "states": states})
    countries.sort(key=lambda item: item["name"].casefold())
    return countries


def _postal_hints(code: str):
    with _lock:
        if code in _postal:
            return _postal[code]
    hints = {"examples": [], "prefixes": {}}
    try:
        payload = _get_json(POSTAL_URL.format(code=code))
    except Exception:
        payload = {}
    examples = [part.strip() for part in (payload.get("zipex") or "").split(",") if part.strip()]
    keys = [part for part in (payload.get("sub_keys") or "").split("~")]
    zips = [part for part in (payload.get("sub_zips") or "").split("~")]
    prefixes = {}
    for key, zip_hint in zip(keys, zips):
        cleaned = zip_hint.replace("|", ", ").strip()
        if key and cleaned:
            prefixes[key] = cleaned
    hints = {"examples": examples, "prefixes": prefixes}
    with _lock:
        _postal[code] = hints
    return hints


def _get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "RegAdmin/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)

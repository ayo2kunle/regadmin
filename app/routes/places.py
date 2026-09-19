from flask import Blueprint, jsonify

from flask_login import login_required

from app.places import country_places, list_countries

places_bp = Blueprint("places", __name__, url_prefix="/places")


@places_bp.route("/countries")
@login_required
def countries():
    try:
        rows = [{"code": country["code"], "name": country["name"]} for country in list_countries()]
    except Exception:
        return jsonify({"error": "The country list is unavailable right now."}), 503
    return jsonify(rows)


@places_bp.route("/countries/<code>")
@login_required
def country(code):
    try:
        detail = country_places(code)
    except Exception:
        return jsonify({"error": "That country's regions are unavailable right now."}), 503
    if detail is None:
        return jsonify({"error": "Unknown country."}), 404
    return jsonify(detail)

from datetime import datetime
from flask import jsonify

VALID_REGIONS = ["CISO", "ERCO"]


def validate_region(region):
    if region not in VALID_REGIONS:
        return jsonify({"error": f"Invalid region. Choose from: {VALID_REGIONS}"}), 400
    return None


def validate_date(value, param_name):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return None
    except ValueError:
        return jsonify({"error": f"Invalid {param_name}. Use YYYY-MM-DD format."}), 400

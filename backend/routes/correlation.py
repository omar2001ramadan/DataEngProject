from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

correlation_bp = Blueprint("correlation", __name__)

VALID_METRICS = ["temperature", "humidity", "wind_speed", "visibility", "pressure"]


@correlation_bp.route("/api/correlation/solar-weather")
def solar_weather_correlation():
    region = request.args.get("region", "CISO")
    metric = request.args.get("metric", "temperature")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if metric not in VALID_METRICS:
        return jsonify({"error": f"Invalid metric. Choose from: {VALID_METRICS}"}), 400

    col_map = {
        "temperature": "avg_temperature",
        "humidity": "avg_humidity",
        "wind_speed": "avg_wind_speed",
        "visibility": "avg_visibility",
        "pressure": "avg_pressure",
    }
    col = col_map[metric]

    where = [f"region = :region", f"{col} IS NOT NULL"]
    params = {"region": region}
    if start_date:
        where.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT date, total_mwh, {col} AS metric_value
        FROM daily_summary
        WHERE {" AND ".join(where)}
        ORDER BY date
    """)

    rows = db.session.execute(query, params).mappings().all()

    # Compute R-squared
    r_squared = None
    if len(rows) > 2:
        x = [float(r["metric_value"]) for r in rows]
        y = [float(r["total_mwh"]) for r in rows]
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(a * b for a, b in zip(x, y))
        sum_x2 = sum(a * a for a in x)
        sum_y2 = sum(b * b for b in y)

        denom = (n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)
        if denom > 0:
            r = (n * sum_xy - sum_x * sum_y) / (denom ** 0.5)
            r_squared = round(r * r, 4)

            # Linear regression coefficients for trendline
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = 0
    else:
        slope = 0
        intercept = 0

    return jsonify({
        "metric": metric,
        "r_squared": r_squared,
        "slope": round(slope, 4),
        "intercept": round(intercept, 2),
        "count": len(rows),
        "data": [{
            "date": str(r["date"]),
            "solar_mwh": round(float(r["total_mwh"]), 1),
            "metric_value": round(float(r["metric_value"]), 2),
        } for r in rows],
    })


@correlation_bp.route("/api/correlation/solar-daylight")
def solar_daylight_correlation():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = ["region = :region", "day_length_seconds IS NOT NULL"]
    params = {"region": region}
    if start_date:
        where.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT date, total_mwh, day_length_seconds
        FROM daily_summary
        WHERE {" AND ".join(where)}
        ORDER BY date
    """)

    rows = db.session.execute(query, params).mappings().all()

    # R-squared for daylight vs solar
    r_squared = None
    if len(rows) > 2:
        x = [float(r["day_length_seconds"]) / 3600 for r in rows]
        y = [float(r["total_mwh"]) for r in rows]
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(a * b for a, b in zip(x, y))
        sum_x2 = sum(a * a for a in x)
        sum_y2 = sum(b * b for b in y)

        denom = (n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)
        if denom > 0:
            r = (n * sum_xy - sum_x * sum_y) / (denom ** 0.5)
            r_squared = round(r * r, 4)
            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = 0
    else:
        slope = 0
        intercept = 0

    return jsonify({
        "r_squared": r_squared,
        "slope": round(slope, 4),
        "intercept": round(intercept, 2),
        "count": len(rows),
        "data": [{
            "date": str(r["date"]),
            "solar_mwh": round(float(r["total_mwh"]), 1),
            "day_length_hours": round(float(r["day_length_seconds"]) / 3600, 2),
        } for r in rows],
    })

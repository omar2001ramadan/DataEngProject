from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

solar_bp = Blueprint("solar", __name__)


@solar_bp.route("/api/solar/daily")
def solar_daily():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = ["region = :region"]
    params = {"region": region}
    if start_date:
        where.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT date, total_mwh, peak_mwh, avg_temperature,
               avg_humidity, day_length_seconds
        FROM daily_summary
        WHERE {" AND ".join(where)}
        ORDER BY date
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "date": str(r["date"]),
        "total_mwh": round(float(r["total_mwh"]), 1),
        "peak_mwh": round(float(r["peak_mwh"]), 1),
        "avg_temperature": round(float(r["avg_temperature"]), 1) if r["avg_temperature"] else None,
        "avg_humidity": round(float(r["avg_humidity"]), 1) if r["avg_humidity"] else None,
        "day_length_hours": round(float(r["day_length_seconds"]) / 3600, 2) if r["day_length_seconds"] else None,
    } for r in rows])


@solar_bp.route("/api/solar/hourly")
def solar_hourly():
    region = request.args.get("region", "CISO")
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date parameter required"}), 400

    query = text("""
        SELECT
            EXTRACT(HOUR FROM s.period)::int AS hour,
            s.value_mwh,
            w.temperature,
            w.humidity,
            w.wind_speed
        FROM solar_generation s
        JOIN regions r ON s.region_id = r.id
        LEFT JOIN weather_stations ws ON ws.region_id = r.id
        LEFT JOIN weather_hourly w
            ON w.station_id = ws.id
            AND DATE(s.period) = DATE(w.hour)
            AND EXTRACT(HOUR FROM s.period) = EXTRACT(HOUR FROM w.hour)
        WHERE r.code = :region AND DATE(s.period) = :date
        ORDER BY hour
    """)

    rows = db.session.execute(query, {"region": region, "date": date}).mappings().all()

    # Get sunrise/sunset for that day
    sun_query = text("""
        SELECT ss.sunrise, ss.sunset FROM sunrise_sunset ss
        JOIN regions r ON ss.region_id = r.id
        WHERE r.code = :region AND ss.date = :date
    """)
    sun = db.session.execute(sun_query, {"region": region, "date": date}).mappings().first()

    result = {
        "hours": [{
            "hour": r["hour"],
            "value_mwh": round(float(r["value_mwh"]), 1),
            "temperature": round(float(r["temperature"]), 1) if r["temperature"] else None,
            "humidity": round(float(r["humidity"]), 1) if r["humidity"] else None,
            "wind_speed": round(float(r["wind_speed"]), 1) if r["wind_speed"] else None,
        } for r in rows],
    }
    if sun:
        result["sunrise"] = sun["sunrise"].strftime("%H:%M") if sun["sunrise"] else None
        result["sunset"] = sun["sunset"].strftime("%H:%M") if sun["sunset"] else None

    return jsonify(result)


@solar_bp.route("/api/solar/monthly")
def solar_monthly():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = ["region = :region"]
    params = {"region": region}
    if start_date:
        where.append("month >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("month <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT month, total_mwh, avg_daily_mwh, peak_mwh,
               avg_temperature, avg_day_length_seconds, days_in_month
        FROM monthly_summary
        WHERE {" AND ".join(where)}
        ORDER BY month
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "month": str(r["month"]),
        "total_mwh": round(float(r["total_mwh"]), 1),
        "avg_daily_mwh": round(float(r["avg_daily_mwh"]), 1),
        "peak_mwh": round(float(r["peak_mwh"]), 1),
        "avg_temperature": round(float(r["avg_temperature"]), 1) if r["avg_temperature"] else None,
        "avg_day_length_hours": round(float(r["avg_day_length_seconds"]) / 3600, 2) if r["avg_day_length_seconds"] else None,
        "days_in_month": r["days_in_month"],
    } for r in rows])


@solar_bp.route("/api/solar/comparison")
def solar_comparison():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = []
    params = {}
    if start_date:
        where.append("month >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("month <= :end_date")
        params["end_date"] = end_date

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    query = text(f"""
        SELECT month, region, total_mwh, avg_daily_mwh
        FROM monthly_summary
        {where_clause}
        ORDER BY month, region
    """)

    rows = db.session.execute(query, params).mappings().all()

    # Pivot: group by month with CISO/ERCO side by side
    months = {}
    for r in rows:
        m = str(r["month"])
        if m not in months:
            months[m] = {"month": m}
        prefix = r["region"].lower()
        months[m][f"{prefix}_total_mwh"] = round(float(r["total_mwh"]), 1)
        months[m][f"{prefix}_avg_daily_mwh"] = round(float(r["avg_daily_mwh"]), 1)

    return jsonify(list(months.values()))

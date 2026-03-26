from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

solar_bp = Blueprint("solar", __name__)


@solar_bp.route("/api/solar/daily")
def solar_daily():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = ["ds.region = :region"]
    params = {"region": region}
    if start_date:
        where.append("ds.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("ds.date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT ds.date, ds.total_mwh, ds.peak_mwh, ds.avg_temperature,
               ds.avg_humidity, ds.avg_wind_speed, ds.avg_visibility,
               ds.avg_pressure, ds.day_length_seconds,
               wx.total_precip, wx.sky_conditions
        FROM daily_summary ds
        LEFT JOIN (
            SELECT DATE(w.observation_datetime) AS pdate, ws.respondent_id AS pregion,
                   SUM(w.precipitation_mm) AS total_precip,
                   MODE() WITHIN GROUP (ORDER BY w.sky_conditions) AS sky_conditions
            FROM weather_observation w
            JOIN weather_station ws ON w.station_id = ws.station_id
            WHERE w.sky_conditions IS NOT NULL
            GROUP BY DATE(w.observation_datetime), ws.respondent_id
        ) wx ON wx.pdate = ds.date AND wx.pregion = ds.region
        WHERE {" AND ".join(where)}
        ORDER BY ds.date
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "date": str(r["date"]),
        "total_mwh": round(float(r["total_mwh"]), 1),
        "peak_mwh": round(float(r["peak_mwh"]), 1),
        "avg_temperature": round(float(r["avg_temperature"]), 1) if r["avg_temperature"] else None,
        "avg_humidity": round(float(r["avg_humidity"]), 1) if r["avg_humidity"] else None,
        "avg_wind_speed": round(float(r["avg_wind_speed"]), 1) if r["avg_wind_speed"] else None,
        "avg_visibility": round(float(r["avg_visibility"]), 1) if r["avg_visibility"] else None,
        "avg_pressure": round(float(r["avg_pressure"]), 1) if r["avg_pressure"] else None,
        "total_precip": round(float(r["total_precip"]), 2) if r["total_precip"] else None,
        "sky_conditions": r["sky_conditions"] if r["sky_conditions"] else None,
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
            AVG(s.value_mwh) AS value_mwh,
            AVG(w.dry_bulb_temp_c) AS temperature,
            AVG(w.relative_humidity_pct) AS humidity,
            AVG(w.wind_speed_kmh) AS wind_speed,
            AVG(w.visibility_km) AS visibility,
            SUM(w.precipitation_mm) AS precipitation,
            MODE() WITHIN GROUP (ORDER BY w.sky_conditions) AS sky_conditions
        FROM solar_generation s
        JOIN respondent r ON s.respondent_id = r.respondent_id
        LEFT JOIN weather_station ws ON ws.respondent_id = r.respondent_id
        LEFT JOIN weather_observation w
            ON w.station_id = ws.station_id
            AND DATE(s.period) = DATE(w.observation_datetime)
            AND EXTRACT(HOUR FROM s.period) = EXTRACT(HOUR FROM w.observation_datetime)
        WHERE r.respondent_id = :region AND DATE(s.period) = :date
        GROUP BY EXTRACT(HOUR FROM s.period)
        ORDER BY hour
    """)

    rows = db.session.execute(query, {"region": region, "date": date}).mappings().all()

    # Get sunrise/sunset for that day
    sun_query = text("""
        SELECT t.sunrise, t.sunset FROM daily_solar_timing t
        WHERE t.respondent_id = :region AND t.date = :date
    """)
    sun = db.session.execute(sun_query, {"region": region, "date": date}).mappings().first()

    result = {
        "hours": [{
            "hour": r["hour"],
            "value_mwh": round(float(r["value_mwh"]), 1),
            "temperature": round(float(r["temperature"]), 1) if r["temperature"] else None,
            "humidity": round(float(r["humidity"]), 1) if r["humidity"] else None,
            "wind_speed": round(float(r["wind_speed"]), 1) if r["wind_speed"] else None,
            "visibility": round(float(r["visibility"]), 1) if r["visibility"] else None,
            "precipitation": round(float(r["precipitation"]), 2) if r["precipitation"] else None,
            "sky_conditions": r["sky_conditions"] if r["sky_conditions"] else None,
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
        SELECT month, region, total_mwh, avg_daily_mwh,
               capacity_mw, capacity_factor_pct
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
        months[m][f"{prefix}_capacity_mw"] = round(float(r["capacity_mw"]), 1) if r["capacity_mw"] else None
        months[m][f"{prefix}_capacity_factor_pct"] = round(float(r["capacity_factor_pct"]), 2) if r["capacity_factor_pct"] else None

    return jsonify(list(months.values()))

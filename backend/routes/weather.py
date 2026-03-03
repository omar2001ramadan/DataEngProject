from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/api/weather/daily")
def weather_daily():
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
        SELECT date, avg_temperature, avg_humidity, avg_wind_speed,
               avg_visibility, avg_pressure
        FROM daily_summary
        WHERE {" AND ".join(where)}
        ORDER BY date
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "date": str(r["date"]),
        "temperature": round(float(r["avg_temperature"]), 1) if r["avg_temperature"] else None,
        "humidity": round(float(r["avg_humidity"]), 1) if r["avg_humidity"] else None,
        "wind_speed": round(float(r["avg_wind_speed"]), 1) if r["avg_wind_speed"] else None,
        "visibility": round(float(r["avg_visibility"]), 1) if r["avg_visibility"] else None,
        "pressure": round(float(r["avg_pressure"]), 1) if r["avg_pressure"] else None,
    } for r in rows])

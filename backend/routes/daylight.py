from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

daylight_bp = Blueprint("daylight", __name__)


@daylight_bp.route("/api/daylight")
def daylight():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = ["r.code = :region"]
    params = {"region": region}
    if start_date:
        where.append("ss.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("ss.date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT
            ss.date,
            ss.sunrise,
            ss.sunset,
            ss.day_length_seconds,
            ds.total_mwh
        FROM sunrise_sunset ss
        JOIN regions r ON ss.region_id = r.id
        LEFT JOIN daily_summary ds
            ON r.code = ds.region AND ss.date = ds.date
        WHERE {" AND ".join(where)}
        ORDER BY ss.date
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "date": str(r["date"]),
        "sunrise": r["sunrise"].strftime("%H:%M") if r["sunrise"] else None,
        "sunset": r["sunset"].strftime("%H:%M") if r["sunset"] else None,
        "day_length_hours": round(float(r["day_length_seconds"]) / 3600, 2) if r["day_length_seconds"] else None,
        "total_mwh": round(float(r["total_mwh"]), 1) if r["total_mwh"] else None,
    } for r in rows])

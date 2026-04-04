from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text
from routes.helpers import validate_region, validate_date

daylight_bp = Blueprint("daylight", __name__)


@daylight_bp.route("/api/daylight")
def daylight():
    region = request.args.get("region", "CISO")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    err = validate_region(region)
    if err:
        return err
    if start_date:
        err = validate_date(start_date, "start_date")
        if err:
            return err
    if end_date:
        err = validate_date(end_date, "end_date")
        if err:
            return err

    where = ["t.respondent_id = :region"]
    params = {"region": region}
    if start_date:
        where.append("t.date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("t.date <= :end_date")
        params["end_date"] = end_date

    query = text(f"""
        SELECT
            t.date,
            t.sunrise,
            t.sunset,
            EXTRACT(EPOCH FROM (t.sunset - t.sunrise))::INT AS day_length_sec,
            ds.total_mwh
        FROM daily_solar_timing t
        LEFT JOIN daily_summary ds
            ON t.respondent_id = ds.region AND t.date = ds.date
        WHERE {" AND ".join(where)}
        ORDER BY t.date
    """)

    rows = db.session.execute(query, params).mappings().all()
    return jsonify([{
        "date": str(r["date"]),
        "sunrise": r["sunrise"].strftime("%H:%M") if r["sunrise"] else None,
        "sunset": r["sunset"].strftime("%H:%M") if r["sunset"] else None,
        "day_length_hours": round(float(r["day_length_sec"]) / 3600, 2) if r["day_length_sec"] else None,
        "total_mwh": round(float(r["total_mwh"]), 1) if r["total_mwh"] else None,
    } for r in rows])

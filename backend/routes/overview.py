from flask import Blueprint, request, jsonify
from models import db
from sqlalchemy import text

overview_bp = Blueprint("overview", __name__)


@overview_bp.route("/api/overview")
def overview():
    region = request.args.get("region")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    where = []
    params = {}
    if region:
        where.append("region = :region")
        params["region"] = region
    if start_date:
        where.append("date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        where.append("date <= :end_date")
        params["end_date"] = end_date

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    query = text(f"""
        SELECT
            COALESCE(SUM(total_mwh), 0) AS total_mwh,
            COALESCE(AVG(total_mwh), 0) AS avg_daily_mwh,
            COALESCE(MAX(peak_mwh), 0) AS peak_mwh,
            MIN(date) AS date_from,
            MAX(date) AS date_to,
            COUNT(*) AS total_days,
            COALESCE(AVG(avg_temperature), 0) AS avg_temperature,
            COALESCE(AVG(day_length_seconds), 0) AS avg_day_length
        FROM daily_summary
        {where_clause}
    """)

    row = db.session.execute(query, params).mappings().first()
    return jsonify({
        "total_mwh": round(float(row["total_mwh"]), 1),
        "avg_daily_mwh": round(float(row["avg_daily_mwh"]), 1),
        "peak_mwh": round(float(row["peak_mwh"]), 1),
        "date_from": str(row["date_from"]) if row["date_from"] else None,
        "date_to": str(row["date_to"]) if row["date_to"] else None,
        "total_days": row["total_days"],
        "avg_temperature": round(float(row["avg_temperature"]), 1),
        "avg_day_length_hours": round(float(row["avg_day_length"]) / 3600, 1),
    })

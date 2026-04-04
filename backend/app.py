import os
from flask import Flask, jsonify
from flask_cors import CORS
from models import db
from sqlalchemy import text
from config import DATABASE_URL
from routes.overview import overview_bp
from routes.solar import solar_bp
from routes.weather import weather_bp
from routes.correlation import correlation_bp
from routes.daylight import daylight_bp


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app, origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ])
    db.init_app(app)

    app.register_blueprint(overview_bp)
    app.register_blueprint(solar_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(correlation_bp)
    app.register_blueprint(daylight_bp)

    @app.errorhandler(Exception)
    def handle_exception(e):
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    @app.route("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok", "database": "connected"}
        except Exception:
            return {"status": "error", "database": "unreachable"}, 503

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(debug=debug, host="0.0.0.0", port=5000)

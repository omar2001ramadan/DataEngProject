from flask import Flask
from flask_cors import CORS
from models import db
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

    CORS(app)
    db.init_app(app)

    app.register_blueprint(overview_bp)
    app.register_blueprint(solar_bp)
    app.register_blueprint(weather_bp)
    app.register_blueprint(correlation_bp)
    app.register_blueprint(daylight_bp)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

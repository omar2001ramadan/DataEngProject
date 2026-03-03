from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Region(db.Model):
    __tablename__ = "regions"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

    stations = db.relationship("WeatherStation", backref="region")
    solar_records = db.relationship("SolarGeneration", backref="region")
    sunrise_records = db.relationship("SunriseSunset", backref="region")


class WeatherStation(db.Model):
    __tablename__ = "weather_stations"
    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False, index=True)
    station_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    weather_records = db.relationship("WeatherHourly", backref="station")


class SolarGeneration(db.Model):
    __tablename__ = "solar_generation"
    id = db.Column(db.Integer, primary_key=True)
    period = db.Column(db.DateTime, nullable=False, index=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False, index=True)
    value_mwh = db.Column(db.Float, nullable=False)


class WeatherHourly(db.Model):
    __tablename__ = "weather_hourly"
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("weather_stations.id"), nullable=False, index=True)
    hour = db.Column(db.DateTime, nullable=False, index=True)
    temperature = db.Column(db.Float)
    dew_point = db.Column(db.Float)
    humidity = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    wind_direction = db.Column(db.String(10))
    wind_gust = db.Column(db.Float)
    precipitation = db.Column(db.Float)
    visibility = db.Column(db.Float)
    pressure = db.Column(db.Float)


class SunriseSunset(db.Model):
    __tablename__ = "sunrise_sunset"
    id = db.Column(db.Integer, primary_key=True)
    region_id = db.Column(db.Integer, db.ForeignKey("regions.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    sunrise = db.Column(db.DateTime, nullable=False)
    sunset = db.Column(db.DateTime, nullable=False)
    day_length_seconds = db.Column(db.Integer, nullable=False)

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class DateDimension(db.Model):
    __tablename__ = "date_dimension"
    date_id = db.Column(db.Date, primary_key=True)
    day_of_week = db.Column(db.String(10))
    month = db.Column(db.Integer)
    month_name = db.Column(db.String(10))
    quarter = db.Column(db.Integer)
    year = db.Column(db.Integer)
    season = db.Column(db.String(10))
    is_weekend = db.Column(db.Boolean)


class Respondent(db.Model):
    __tablename__ = "respondent"
    respondent_id = db.Column(db.String(10), primary_key=True)
    respondent_name = db.Column(db.String(255), nullable=False)
    region_latitude = db.Column(db.Float)
    region_longitude = db.Column(db.Float)

    stations = db.relationship("WeatherStation", backref="respondent")
    solar_records = db.relationship("SolarGeneration", backref="respondent")
    timing_records = db.relationship("DailySolarTiming", backref="respondent")


class WeatherStation(db.Model):
    __tablename__ = "weather_station"
    station_id = db.Column(db.String(50), primary_key=True)
    station_name = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    respondent_id = db.Column(db.String(10), db.ForeignKey("respondent.respondent_id"), nullable=False, index=True)

    observations = db.relationship("WeatherObservation", backref="station")


class SolarGeneration(db.Model):
    __tablename__ = "solar_generation"
    generation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondent_id = db.Column(db.String(10), db.ForeignKey("respondent.respondent_id"), nullable=False, index=True)
    period = db.Column(db.DateTime, nullable=False, index=True)
    date_id = db.Column(db.Date, db.ForeignKey("date_dimension.date_id"), nullable=False)
    value_mwh = db.Column(db.Float, nullable=False)


class WeatherObservation(db.Model):
    __tablename__ = "weather_observation"
    observation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    station_id = db.Column(db.String(50), db.ForeignKey("weather_station.station_id"), index=True)
    date_id = db.Column(db.Date, db.ForeignKey("date_dimension.date_id"))
    observation_datetime = db.Column(db.DateTime, index=True)
    dry_bulb_temp_c = db.Column(db.Float)
    dew_point_temp_c = db.Column(db.Float)
    relative_humidity_pct = db.Column(db.Float)
    wet_bulb_temp_c = db.Column(db.Float)
    wind_speed_kmh = db.Column(db.Float)
    wind_direction_deg = db.Column(db.Integer)
    wind_gust_speed_kmh = db.Column(db.Float)
    precipitation_mm = db.Column(db.Float)
    sky_conditions = db.Column(db.String(100))
    visibility_km = db.Column(db.Float)
    station_pressure_hpa = db.Column(db.Float)
    altimeter_setting_hpa = db.Column(db.Float)


class DailySolarTiming(db.Model):
    __tablename__ = "daily_solar_timing"
    timing_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    respondent_id = db.Column(db.String(10), db.ForeignKey("respondent.respondent_id"), nullable=False, index=True)
    date_id = db.Column(db.Date, db.ForeignKey("date_dimension.date_id"))
    date = db.Column(db.Date, nullable=False, index=True)
    sunrise = db.Column(db.DateTime)
    sunset = db.Column(db.DateTime)
    solar_noon = db.Column(db.DateTime)
    day_length_sec = db.Column(db.Integer)
    civil_twilight_begin = db.Column(db.DateTime)
    civil_twilight_end = db.Column(db.DateTime)
    nautical_twilight_begin = db.Column(db.DateTime)
    nautical_twilight_end = db.Column(db.DateTime)
    astronomical_twilight_begin = db.Column(db.DateTime)
    astronomical_twilight_end = db.Column(db.DateTime)

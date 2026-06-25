from datetime import datetime
from timeutil import utcnow

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Commodity(db.Model):
    __tablename__ = "commodities"

    id = db.Column(db.String(16), primary_key=True)  # e.g. 'wti'
    name = db.Column(db.String(64), nullable=False)
    unit = db.Column(db.String(16), nullable=False)
    category = db.Column(db.String(32))
    yahoo_symbol = db.Column(db.String(16))   # e.g. 'CL=F'  (primary source)
    stooq_symbol = db.Column(db.String(16))   # e.g. 'cl.f'  (fallback source)


class PriceTick(db.Model):
    __tablename__ = "price_ticks"

    id = db.Column(db.Integer, primary_key=True)
    commodity_id = db.Column(db.String(16), db.ForeignKey("commodities.id"), index=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(32), nullable=False)  # 'yahoo' | 'stooq'
    fetched_at = db.Column(db.DateTime, default=utcnow, index=True)


class FacilityWeather(db.Model):
    __tablename__ = "facility_weather"

    id = db.Column(db.Integer, primary_key=True)
    facility_name = db.Column(db.String(128), index=True, nullable=False)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    temp_c = db.Column(db.Float)
    cloud_pct = db.Column(db.Float)
    wind_kmh = db.Column(db.Float)
    precip_mm = db.Column(db.Float)
    fetched_at = db.Column(db.DateTime, default=utcnow, index=True)


class MacroReading(db.Model):
    __tablename__ = "macro_readings"

    id = db.Column(db.Integer, primary_key=True)
    dxy = db.Column(db.Float)
    fetched_at = db.Column(db.DateTime, default=utcnow, index=True)


class NewsEvent(db.Model):
    """Placeholder for a real news pipeline (e.g. a news-API integration).
    Not populated automatically by this scaffold — wire up a collector the
    same way price/weather collectors work, and insert rows here."""
    __tablename__ = "news_events"

    id = db.Column(db.Integer, primary_key=True)
    commodity_id = db.Column(db.String(16), index=True)
    kind = db.Column(db.String(16))  # 'news' | 'weather' | 'macro'
    headline = db.Column(db.String(512))
    sentiment = db.Column(db.Float)
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    location_label = db.Column(db.String(128))
    source = db.Column(db.String(64))
    published_at = db.Column(db.DateTime, default=utcnow, index=True)

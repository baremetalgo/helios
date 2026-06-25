import logging
from datetime import datetime, timedelta
from timeutil import utcnow

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from models import db, Commodity, PriceTick, FacilityWeather, MacroReading, NewsEvent
from scheduler import init_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Keep these in sync with COMMODITIES in the frontend (helios.html)
SEED_COMMODITIES = [
    dict(id="wti", name="WTI Crude Oil", unit="$/bbl", category="Energy", yahoo_symbol="CL=F", stooq_symbol="cl.f"),
    dict(id="brent", name="Brent Crude", unit="$/bbl", category="Energy", yahoo_symbol="BZ=F", stooq_symbol="bz.f"),
    dict(id="ng", name="Henry Hub Nat. Gas", unit="$/MMBtu", category="Energy", yahoo_symbol="NG=F", stooq_symbol="ng.f"),
    dict(id="cu", name="Copper", unit="$/lb", category="Metals", yahoo_symbol="HG=F", stooq_symbol="hg.f"),
    dict(id="au", name="Gold", unit="$/oz", category="Precious", yahoo_symbol="GC=F", stooq_symbol="gc.f"),
    dict(id="ag", name="Silver", unit="$/oz", category="Precious", yahoo_symbol="SI=F", stooq_symbol="si.f"),
    dict(id="wheat", name="Wheat", unit="cents/bu", category="Agriculture", yahoo_symbol="ZW=F", stooq_symbol="zw.f"),
    dict(id="coffee", name="Coffee Arabica", unit="cents/lb", category="Agriculture", yahoo_symbol="KC=F", stooq_symbol="kc.f"),
]


def create_app(config_overrides: dict = None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    with app.app_context():
        db.create_all()
        for c in SEED_COMMODITIES:
            if not db.session.get(Commodity, c["id"]):
                db.session.add(Commodity(**c))
        db.session.commit()

    register_routes(app)

    if not app.config.get("DISABLE_SCHEDULER"):
        init_scheduler(app)

    return app


def register_routes(app):

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", time=utcnow().isoformat())

    @app.get("/api/commodities")
    def list_commodities():
        rows = Commodity.query.all()
        return jsonify([
            dict(id=c.id, name=c.name, unit=c.unit, category=c.category) for c in rows
        ])

    @app.get("/api/prices/<commodity_id>/latest")
    def latest_price(commodity_id):
        tick = (PriceTick.query
                .filter_by(commodity_id=commodity_id)
                .order_by(PriceTick.fetched_at.desc())
                .first())
        if not tick:
            return jsonify(error="no data yet — has the scheduler had a cycle to run?"), 404
        return jsonify(
            commodity_id=commodity_id,
            price=tick.price,
            source=tick.source,
            fetched_at=tick.fetched_at.isoformat() + "Z",
        )

    @app.get("/api/prices/<commodity_id>/history")
    def price_history(commodity_id):
        hours = int(request.args.get("hours", 720))
        since = utcnow() - timedelta(hours=hours)
        rows = (PriceTick.query
                .filter(PriceTick.commodity_id == commodity_id, PriceTick.fetched_at >= since)
                .order_by(PriceTick.fetched_at.asc())
                .all())
        return jsonify([
            dict(price=r.price, source=r.source, fetched_at=r.fetched_at.isoformat() + "Z") for r in rows
        ])

    @app.get("/api/weather/<facility_name>/latest")
    def latest_weather(facility_name):
        row = (FacilityWeather.query
               .filter_by(facility_name=facility_name)
               .order_by(FacilityWeather.fetched_at.desc())
               .first())
        if not row:
            return jsonify(error="no data yet"), 404
        return jsonify(
            facility_name=row.facility_name,
            temp_c=row.temp_c, cloud_pct=row.cloud_pct,
            wind_kmh=row.wind_kmh, precip_mm=row.precip_mm,
            fetched_at=row.fetched_at.isoformat() + "Z",
        )

    @app.get("/api/macro/dxy/latest")
    def latest_dxy():
        row = MacroReading.query.order_by(MacroReading.fetched_at.desc()).first()
        if not row:
            return jsonify(error="no data yet"), 404
        return jsonify(dxy=row.dxy, fetched_at=row.fetched_at.isoformat() + "Z")

    @app.get("/api/macro/dxy/history")
    def dxy_history():
        hours = int(request.args.get("hours", 720))
        since = utcnow() - timedelta(hours=hours)
        rows = (MacroReading.query
                .filter(MacroReading.fetched_at >= since)
                .order_by(MacroReading.fetched_at.asc())
                .all())
        return jsonify([dict(dxy=r.dxy, fetched_at=r.fetched_at.isoformat() + "Z") for r in rows])

    @app.get("/api/news")
    def list_news():
        commodity_id = request.args.get("commodity_id")
        q = NewsEvent.query
        if commodity_id:
            q = q.filter_by(commodity_id=commodity_id)
        rows = q.order_by(NewsEvent.published_at.desc()).limit(100).all()
        return jsonify([
            dict(
                commodity_id=r.commodity_id, kind=r.kind, headline=r.headline,
                sentiment=r.sentiment, lat=r.lat, lon=r.lon, location_label=r.location_label,
                source=r.source, published_at=r.published_at.isoformat() + "Z",
            ) for r in rows
        ])


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

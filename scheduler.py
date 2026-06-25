import logging
from datetime import datetime
from timeutil import utcnow

from apscheduler.schedulers.background import BackgroundScheduler

from collectors import fetch_yahoo_price, fetch_stooq_price, fetch_open_meteo, fetch_dxy
from models import db, Commodity, PriceTick, FacilityWeather, MacroReading

log = logging.getLogger(__name__)

# Keep this list in sync with the facility list in the frontend (helios.html).
# name, lat, lon
FACILITIES = [
    ("Permian Basin", 31.87, -102.28),
    ("Cushing Hub", 35.98, -96.77),
    ("Gulf Coast Refining", 29.75, -95.36),
    ("Forties Field", 58.4, 1.8),
    ("Johan Sverdrup", 59.0, 2.9),
    ("Rotterdam Terminal", 51.9, 4.5),
    ("Henry Hub", 29.86, -92.12),
    ("Marcellus Shale", 41.2, -77.0),
    ("Qatar North Field", 25.4, 51.5),
    ("Escondida Mine", -24.27, -69.07),
    ("Grasberg Mine", -4.05, 137.11),
    ("Kamoa-Kakula", -10.75, 25.4),
    ("Witwatersrand Basin", -26.2, 27.5),
    ("Carlin Trend", 40.77, -116.34),
    ("Muruntau Mine", 41.45, 64.58),
    ("Fresnillo Mine", 23.18, -102.87),
    ("Pirquitas Mine", -22.69, -66.0),
    ("Black Sea Region", 49.0, 32.0),
    ("Kansas Belt", 38.5, -98.0),
    ("Punjab Belt", 31.1, 75.3),
    ("Minas Gerais", -19.0, -44.0),
    ("Central Highlands", 12.7, 108.0),
]


def poll_prices(app):
    with app.app_context():
        inserted = 0
        for c in Commodity.query.all():
            price = fetch_yahoo_price(c.yahoo_symbol)
            source = "yahoo"
            if price is None:
                price = fetch_stooq_price(c.stooq_symbol)
                source = "stooq"
            if price is None:
                log.warning("poll_prices: no live price for %s this cycle", c.id)
                continue
            db.session.add(PriceTick(commodity_id=c.id, price=price, source=source))
            inserted += 1
        db.session.commit()
        log.info("poll_prices: inserted %d ticks at %s", inserted, utcnow().isoformat())


def poll_weather(app):
    with app.app_context():
        inserted = 0
        for name, lat, lon in FACILITIES:
            wx = fetch_open_meteo(lat, lon)
            if not wx:
                continue
            db.session.add(FacilityWeather(facility_name=name, lat=lat, lon=lon, **wx))
            inserted += 1
        db.session.commit()
        log.info("poll_weather: inserted %d readings at %s", inserted, utcnow().isoformat())


def poll_macro(app):
    with app.app_context():
        dxy = fetch_dxy()
        if dxy is None:
            log.warning("poll_macro: no DXY reading this cycle")
            return
        db.session.add(MacroReading(dxy=dxy))
        db.session.commit()
        log.info("poll_macro: DXY=%s at %s", dxy, utcnow().isoformat())


def init_scheduler(app):
    sched = BackgroundScheduler(timezone="UTC")
    now = utcnow()
    sched.add_job(lambda: poll_prices(app), "interval",
                  minutes=app.config["POLL_PRICE_MINUTES"], next_run_time=now, id="poll_prices")
    sched.add_job(lambda: poll_weather(app), "interval",
                  minutes=app.config["POLL_WEATHER_MINUTES"], next_run_time=now, id="poll_weather")
    sched.add_job(lambda: poll_macro(app), "interval",
                  minutes=app.config["POLL_MACRO_MINUTES"], next_run_time=now, id="poll_macro")
    sched.start()
    log.info("scheduler started: prices every %dm, weather every %dm, macro every %dm",
              app.config["POLL_PRICE_MINUTES"], app.config["POLL_WEATHER_MINUTES"], app.config["POLL_MACRO_MINUTES"])
    return sched

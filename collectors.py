"""
Server-side data collectors.

The key reason this lives in a backend at all: a browser fetch() to Yahoo
Finance, Stooq, NSE, or MCX gets blocked by CORS because those sites don't
send permissive Access-Control-Allow-Origin headers. A Python process making
the same request server-to-server has no such restriction — CORS is a
browser-enforced policy, not a server one. That's the whole point of this
service existing.

Every function here returns None on failure instead of raising, so a flaky
upstream source never takes the scheduler down.
"""

import logging

import requests

log = logging.getLogger(__name__)

REQUEST_TIMEOUT = 8
UA_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; HeliosCollector/1.0)"}


def fetch_yahoo_price(symbol: str):
    """Primary price source. Uses Yahoo's public chart endpoint.
    Note: this is an unofficial/unauthenticated endpoint — it can change
    shape or start rate-limiting without notice. Treat it as best-effort,
    same as any other free data source, and keep the Stooq fallback below."""
    if not symbol:
        return None
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
            params={"interval": "1m", "range": "1d"},
            headers=UA_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        price = result["meta"].get("regularMarketPrice")
        return float(price) if price is not None else None
    except Exception as e:
        log.warning("Yahoo fetch failed for %s: %s", symbol, e)
        return None


def fetch_stooq_price(stooq_symbol: str):
    """Fallback price source if Yahoo is unavailable."""
    if not stooq_symbol:
        return None
    try:
        r = requests.get(
            "https://stooq.com/q/l/",
            params={"s": stooq_symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
            headers=UA_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if len(lines) < 2:
            return None
        cols = lines[1].split(",")
        price = float(cols[6])
        return price if price > 0 else None
    except Exception as e:
        log.warning("Stooq fetch failed for %s: %s", stooq_symbol, e)
        return None


def fetch_open_meteo(lat: float, lon: float):
    """Free, keyless weather API. Reliable for current conditions at a point."""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,cloud_cover,precipitation,wind_speed_10m",
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        cur = r.json()["current"]
        return {
            "temp_c": cur.get("temperature_2m"),
            "cloud_pct": cur.get("cloud_cover"),
            "wind_kmh": cur.get("wind_speed_10m"),
            "precip_mm": cur.get("precipitation"),
        }
    except Exception as e:
        log.warning("Open-Meteo fetch failed for (%s, %s): %s", lat, lon, e)
        return None


def fetch_dxy():
    """US Dollar Index via Yahoo. Tries the futures ticker, then the index ticker."""
    for symbol in ("DX-Y.NYB", "DX=F"):
        price = fetch_yahoo_price(symbol)
        if price:
            return price
    return None

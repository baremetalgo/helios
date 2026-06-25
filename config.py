import os


class Config:
    """All settings are overridable via environment variables so this can move
    from a laptop to a real server without touching code."""

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///helios.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # how often background jobs run
    POLL_PRICE_MINUTES = int(os.environ.get("POLL_PRICE_MINUTES", 5))
    POLL_WEATHER_MINUTES = int(os.environ.get("POLL_WEATHER_MINUTES", 15))
    POLL_MACRO_MINUTES = int(os.environ.get("POLL_MACRO_MINUTES", 5))

    # CORS — open by default for local dev; set to your real frontend origin in production
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    # set DISABLE_SCHEDULER=1 to run the API without the background pollers
    # (useful for tests, or if you want to trigger polling manually via cron instead)
    DISABLE_SCHEDULER = os.environ.get("DISABLE_SCHEDULER", "0") == "1"

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime — matches what datetime.utcnow() used to return,
    just without the Python 3.12 deprecation warning. Keeping it naive (no
    tzinfo) is intentional so it compares cleanly with existing SQLite rows
    and with timedelta arithmetic elsewhere in this codebase."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

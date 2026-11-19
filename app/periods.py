from datetime import datetime, timedelta, timezone


def utc_string(value):
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def month_bounds(now=None):
    now = now or datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must include a timezone.")

    now = now.astimezone(timezone.utc)

    start = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    end = (start + timedelta(days=32)).replace(day=1)

    return utc_string(start), utc_string(end)
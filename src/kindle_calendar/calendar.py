"""Deterministic Spanish layout, independent of the host locale."""
import calendar
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ZONE = "America/Argentina/Buenos_Aires"
MONTHS = ("", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
          "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
WEEKDAYS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def month_rows(day):
    return calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(day.year, day.month)


def local_day(now):
    if now.tzinfo is None:
        raise ValueError("Se necesita una hora con zona horaria")
    return now.astimezone(ZoneInfo(ZONE)).date()


def next_midnight(now):
    """Calendar arithmetic in the target zone; elapsed seconds measured in UTC."""
    tomorrow = local_day(now) + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, ZoneInfo(ZONE))


def wake_plan(now):
    target = next_midnight(now)
    seconds = (target.astimezone(timezone.utc) - now.astimezone(timezone.utc)).total_seconds()
    return {"date": local_day(now).isoformat(), "next_midnight": target.isoformat(),
            "seconds": seconds, "timezone": ZONE}


def dates(start, end):
    if end < start:
        raise ValueError("La fecha final precede a la inicial")
    day = start
    while True:
        yield day
        if day == end:
            break
        day += timedelta(days=1)

#!/usr/bin/env python3
"""Run a reproducible year-boundary, offline event scenario."""
import json
from datetime import datetime
from kindle_calendar.simulation import Simulator

sim = Simulator(["2026-12-31", "2027-01-01", "2027-01-04"], display_failures=1, rtc_failures=1)
for kind, timestamp in [
    ("startup", "2026-12-31T21:00:00-03:00"),
    ("sleep", "2026-12-31T23:59:00-03:00"),
    ("ready-to-suspend", "2026-12-31T23:59:10-03:00"),
    ("midnight", "2027-01-01T00:00:00-03:00"),
    ("ready-to-suspend", "2027-01-01T00:00:15-03:00"),
    ("clock-change", "2027-01-04T03:00:00-03:00"),
    ("resume", "2027-01-04T08:00:00-03:00"),
]:
    sim.event(kind, datetime.fromisoformat(timestamp))
print(json.dumps(sim.log, ensure_ascii=False, indent=2))

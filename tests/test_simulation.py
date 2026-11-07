import unittest
from datetime import datetime
from kindle_calendar.simulation import Simulator


def now(value):
    return datetime.fromisoformat(value)


class SchedulerModelTests(unittest.TestCase):
    def test_midnight_while_sleeping_and_reading(self):
        sim = Simulator(["2026-12-31", "2027-01-01"])
        sim.event("sleep", now("2026-12-31T23:50:00-03:00"))
        result = sim.event("ready-to-suspend", now("2026-12-31T23:55:00-03:00"))
        self.assertEqual(result["actions"], [{"arm": "2027-01-01T00:00:00-03:00"}])
        sim.event("midnight", now("2027-01-01T00:00:00-03:00"))
        self.assertEqual(sim.displayed, "2027-01-01")
        sim.event("resume", now("2027-01-01T00:01:00-03:00"))
        self.assertEqual(sim.event("midnight", now("2027-01-02T00:00:00-03:00"))["actions"],
                         [{"skip": "reading"}])

    def test_clock_forward_backward_missed_days_and_reboot(self):
        sim = Simulator(["2028-02-29", "2028-03-04"])
        sim.event("sleep", now("2028-02-29T23:00:00-03:00"))
        sim.event("clock-change", now("2028-03-04T08:00:00-03:00"))
        self.assertEqual(sim.displayed, "2028-03-04")
        sim.event("clock-change", now("2028-02-29T22:00:00-03:00"))
        self.assertEqual(sim.displayed, "2028-02-29")
        sim.event("startup", now("2028-03-04T09:00:00-03:00"))
        sim.event("sleep", now("2028-03-04T09:01:00-03:00"))
        self.assertEqual(sim.displayed, "2028-03-04")

    def test_bounded_failures_and_missing_image(self):
        sim = Simulator(["2026-11-06"], display_failures=10, rtc_failures=10)
        result = sim.event("sleep", now("2026-11-06T22:00:00-03:00"))
        self.assertEqual(len(result["actions"]), 4)
        self.assertIsNone(sim.displayed)
        result = sim.event("ready-to-suspend", now("2026-11-06T22:01:00-03:00"))
        self.assertEqual(result["actions"][-1], {"error": "rtc-unarmed"})
        result = sim.event("midnight", now("2026-11-07T00:00:00-03:00"))
        self.assertEqual(result["actions"][0]["error"], "missing-image")

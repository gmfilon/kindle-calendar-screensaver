import calendar
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from kindle_calendar.calendar import dates, local_day, month_rows, wake_plan
from kindle_calendar.generator import digest, generate, render, verify


class CalendarTests(unittest.TestCase):
    def test_complete_gregorian_cycle(self):
        # Every month shape, including Gregorian century leap exceptions.
        for year in range(2000, 2400):
            for month in range(1, 13):
                rows = month_rows(date(year, month, 1))
                values = [n for row in rows for n in row if n]
                self.assertEqual(values, list(range(1, calendar.monthrange(year, month)[1]+1)))
                self.assertEqual(rows[0].index(1), date(year, month, 1).weekday())

    def test_leap_and_year_dates(self):
        self.assertEqual(len(list(dates(date(2028, 1, 1), date(2028, 12, 31)))), 366)
        self.assertEqual(list(dates(date(2026, 12, 31), date(2027, 1, 1))),
                         [date(2026, 12, 31), date(2027, 1, 1)])
        with self.assertRaises(ValueError):
            list(dates(date(2027, 1, 1), date(2026, 12, 31)))

    def test_zone_midnight_and_boundaries(self):
        cases = [
            ("2026-11-07T02:59:59+00:00", "2026-11-06", "2026-11-07T00:00:00-03:00", 1),
            ("2026-12-31T23:59:59-03:00", "2026-12-31", "2027-01-01T00:00:00-03:00", 1),
            ("2028-02-28T23:59:59-03:00", "2028-02-28", "2028-02-29T00:00:00-03:00", 1),
            ("2028-02-29T00:00:00-03:00", "2028-02-29", "2028-03-01T00:00:00-03:00", 86400),
        ]
        for timestamp, day, midnight, seconds in cases:
            with self.subTest(timestamp=timestamp):
                result = wake_plan(datetime.fromisoformat(timestamp))
                self.assertEqual((result["date"], result["next_midnight"], result["seconds"]),
                                 (day, midnight, seconds))
        with self.assertRaises(ValueError):
            local_day(datetime(2026, 1, 1))

    def test_bundle_integrity_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/"a", Path(directory)/"b"
            start, end = date(2028, 2, 28), date(2028, 3, 1)
            generate(start, end, a, (636, 848))
            generate(start, end, b, (636, 848))
            self.assertEqual(len(verify(a)["images"]), 3)
            for file in a.iterdir():
                self.assertEqual(digest(file), digest(b/file.name))
            with self.assertRaises(ValueError):
                generate(start, end, a)
            (a/"2028-02-29.png").write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                verify(a)

    def test_selected_cell_is_black_with_white_numeral(self):
        image = render(date(2026, 11, 6))
        self.assertEqual(image.mode, "L")
        self.assertEqual(image.size, (1272, 1696))
        self.assertEqual(image.getpixel((745, 945)), 0)
        self.assertEqual(image.getpixel((100, 100)), 255)
        # A six-week month must fit too.
        render(date(2026, 3, 31))

    def test_manifest_cannot_select_path_outside_bundle(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory)/"bundle"
            generate(date(2026, 11, 6), date(2026, 11, 6), bundle, (636, 848))
            path = bundle/"manifest.json"
            manifest = json.loads(path.read_text())
            manifest["images"]["2026-11-06"]["file"] = "../outside.png"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                verify(bundle)

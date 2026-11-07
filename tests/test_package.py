import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from kindle_calendar.deployment import install
from kindle_calendar.generator import generate
from tools.package import package


class PackageTests(unittest.TestCase):
    def test_reproducible_disabled_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root/"images"
            generate(date(2026, 11, 6), date(2026, 11, 6), bundle, (636, 848))
            target, _ = install(bundle, root/"staging")
            a, b = root/"a.zip", root/"b.zip"
            self.assertEqual(package(target, a), package(target, b))
            with zipfile.ZipFile(a) as archive:
                self.assertIsNone(archive.testzip())
                self.assertIn("kindle-calendar/DISABLED", archive.namelist())
                self.assertIn("kindle-calendar/state/", archive.namelist())
                self.assertNotIn("kindle-calendar/backend", archive.namelist())
            with self.assertRaises(FileExistsError):
                package(target, a)

    def test_modified_staging_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generate(date(2026, 11, 6), date(2026, 11, 6), root/"images", (636, 848))
            target, _ = install(root/"images", root/"staging")
            (target/"device"/"notes.txt").write_text("changed")
            with self.assertRaises(ValueError):
                package(target, root/"bad.zip")
            self.assertFalse((root/"bad.zip").exists())

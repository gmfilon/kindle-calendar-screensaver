import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from kindle_calendar.deployment import install, safe_root, uninstall
from kindle_calendar.generator import generate


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root/"bundle"
        generate(date(2026, 11, 6), date(2026, 11, 6), self.bundle, (636, 848))

    def test_stage_rollback_and_repeat(self):
        destination = self.root/"staging"
        unrelated = destination/"other-book.txt"
        destination.mkdir()
        unrelated.write_text("keep")
        target, count = install(self.bundle, destination)
        self.assertEqual(count, 1)
        self.assertTrue((target/"DISABLED").exists())
        with self.assertRaises(ValueError):
            install(self.bundle, destination)
        uninstall(destination)
        self.assertFalse(target.exists())
        self.assertEqual(unrelated.read_text(), "keep")
        install(self.bundle, destination)

    def test_modified_or_unowned_data_preserved(self):
        target, _ = install(self.bundle, self.root/"staging")
        (target/"images"/"my-notes.txt").write_text("keep")
        with self.assertRaises(ValueError):
            uninstall(self.root/"staging")
        self.assertTrue((target/"images"/"my-notes.txt").exists())

    def test_copy_failure_leaves_no_partial_install(self):
        with patch("kindle_calendar.deployment.shutil.copytree", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                install(self.bundle, self.root/"staging")
        self.assertEqual(list((self.root/"staging").iterdir()), [])

    def test_reject_system_device_and_symlink_roots(self):
        for path in ("/", "/mnt/us", "/Volumes/Kindle", "/sys/calendar", "/etc/calendar"):
            with self.assertRaises(ValueError):
                safe_root(path)
        alias = self.root/"alias"
        alias.symlink_to("/mnt/us")
        with self.assertRaises(ValueError):
            safe_root(alias)

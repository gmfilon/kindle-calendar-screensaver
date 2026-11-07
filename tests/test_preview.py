"""Guard and restoration checks for the one-shot visual test; no real display."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "device/kpm-calendar-preview/launch.sh"


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "calendar check"
        self.root.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.fb = self.root / "fb0"
        self.fb.mkdir()
        for name, value in (("virtual_size", "1272,3392"), ("bits_per_pixel", "8"), ("rotate", "0")):
            (self.fb/name).write_text(value+"\n")
        (self.root/"OWNER.txt").write_text("kindle-calendar-check-v1\n")
        shutil.copy2(ROOT/"preview/current/2026-11-06.png", self.root/"calendar-test.png")
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ["PATH"],
                        CALENDAR_CHECK_ROOT=str(self.root), CALENDAR_SYSFS_FB0=str(self.fb),
                        CALENDAR_FBINK=str(self.bin/"fbink"), PREVIEW_CALLS=str(self.root/"calls"))
        self.shell("fbink", '''case "$1" in
--help) echo 'FBInk [Image='"${TEST_IMAGE_SUPPORT:-Yes}"']' ;;
-e) echo 'screenWidth=1272;screenHeight=1696;' ;;
*) echo draw >> "$PREVIEW_CALLS"; exit "${TEST_DRAW_FAILURE:-0}" ;;
esac
''')
        self.shell("xrefresh", 'echo restore >> "$PREVIEW_CALLS"\nexit "${TEST_REDRAW_FAILURE:-0}"\n')
        self.shell("sleep", 'echo "sleep-$1" >> "$PREVIEW_CALLS"\n')
        if not shutil.which("timeout"):
            self.shell("timeout", 'shift 3\nexec "$@"\n')
        if not shutil.which("flock"):
            self.program("flock", "import fcntl, sys\nfcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX | fcntl.LOCK_NB)\n")
        if not shutil.which("sha256sum"):
            self.program("sha256sum", "import pathlib, hashlib, sys\nprint(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(), sys.argv[1])\n")

    def shell(self, name, body):
        path = self.bin/name
        path.write_text("#!/bin/sh\nset -eu\n"+body)
        path.chmod(0o755)

    def program(self, name, body):
        path = self.bin/name
        path.write_text(f"#!{sys.executable}\n"+body)
        path.chmod(0o755)

    def run_preview(self):
        return subprocess.run(["sh", str(SCRIPT)], env=self.env, text=True,
                              capture_output=True, timeout=5)

    def test_success_draws_once_and_requests_redraw_after_delay(self):
        result = self.run_preview()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["restore", "sleep-2", "draw", "sleep-25", "restore"])
        log = (self.root/"preview.log").read_text()
        self.assertIn("IMAGE_REFRESH_CONFIRMED=1", log)
        self.assertIn("UI_REDRAW_REQUESTED=1", log)

    def test_failed_render_still_requests_ui_redraw(self):
        self.env["TEST_DRAW_FAILURE"] = "1"
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["restore", "sleep-2", "draw", "restore"])

    def test_ui_redraw_must_work_before_image_is_drawn(self):
        self.env["TEST_REDRAW_FAILURE"] = "1"
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["restore"])

    def test_bad_image_is_rejected_before_display_access(self):
        (self.root/"calendar-test.png").write_bytes(b"corrupt")
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertFalse((self.root/"calls").exists())

    def test_unknown_geometry_is_rejected_before_display_access(self):
        (self.fb/"virtual_size").write_text("600,800\n")
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertFalse((self.root/"calls").exists())

    def test_image_support_must_be_present(self):
        self.env["TEST_IMAGE_SUPPORT"] = "No"
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertFalse((self.root/"calls").exists())

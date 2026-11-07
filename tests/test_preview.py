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
-v) if read -r line; then exit 2; fi; exit "${TEST_INIT_FAILURE:-0}" ;;
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

    def run_preview(self, *args):
        return subprocess.run(["sh", str(SCRIPT), *args], env=self.env, text=True,
                              capture_output=True, timeout=5)

    def mock_sleep_transition(self, state):
        self.env["TEST_SLEEP_STATE"] = state
        self.shell("lipc-get-prop", '''case "$2" in
isCharging|preventScreenSaver) echo 0 ;;
state) if [ -f "$CALENDAR_CHECK_ROOT/ready" ]; then echo "$TEST_SLEEP_STATE"; else echo active; fi ;;
*) exit 2 ;;
esac
''')
        self.shell("lipc-wait-event", '''[ "$4" = readyToSuspend ]
touch "$CALENDAR_CHECK_ROOT/ready"
echo 10
''')

    def mock_renderer(self, modules):
        self.mock_sleep_transition("readyToSuspend")
        self.env["CALENDAR_SCREEN_RESTORE"] = str(self.root/"restore")
        (self.root/"modules").write_text(modules+"\n")
        self.shell("lipc-get-prop", '''case "$2" in
load) cat "$CALENDAR_CHECK_ROOT/modules" ;;
isCharging|preventScreenSaver) echo 0 ;;
state) if [ -f "$CALENDAR_CHECK_ROOT/ready" ]; then echo readyToSuspend; else echo active; fi ;;
*) exit 2 ;;
esac
''')
        self.shell("lipc-set-prop", '''[ "$1" = com.lab126.blanket ] && [ "$3" = screensaver ]
case "$2" in
unload) echo splash > "$CALENDAR_CHECK_ROOT/modules" ;;
load) echo 'splash screensaver' > "$CALENDAR_CHECK_ROOT/modules" ;;
*) exit 2 ;;
esac
echo "$2" >> "$PREVIEW_CALLS"
''')
        self.shell("lipc-wait-event", '''case "$4" in
readyToSuspend) touch "$CALENDAR_CHECK_ROOT/ready"; echo 10 ;;
outOfScreenSaver,goingToPasswdDlg) echo 1 ;;
*) exit 2 ;;
esac
''')

    def test_managed_sleep_restores_stock_even_when_draw_fails(self):
        self.mock_renderer("splash screensaver")
        self.env["TEST_DRAW_FAILURE"] = "1"
        self.assertNotEqual(self.run_preview("managed-sleep").returncode, 0)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["unload", "draw", "load"])
        self.assertFalse((self.root/"restore").exists())

    def test_managed_sleep_does_not_touch_ad_renderer(self):
        self.mock_renderer("screensaver ad_screensaver")
        self.assertNotEqual(self.run_preview("managed-sleep").returncode, 0)
        self.assertFalse((self.root/"calls").exists())

    def test_managed_sleep_recovers_interrupted_test_before_waiting_for_sleep(self):
        self.mock_renderer("splash")
        (self.root/"restore").write_text("screensaver\n")
        result = self.run_preview("managed-sleep")
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["load"])
        self.assertFalse((self.root/"restore").exists())
        self.assertFalse((self.root/"ready").exists())

    def test_restore_waits_for_blanket_to_register_the_renderer(self):
        self.mock_renderer("splash")
        (self.root/"restore").write_text("screensaver\n")
        self.shell("lipc-set-prop", 'echo "splash screensaver" > "$CALENDAR_CHECK_ROOT/pending"\n')
        self.shell("lipc-get-prop", '''[ "$2" = load ]
cat "$CALENDAR_CHECK_ROOT/modules"
if [ -f "$CALENDAR_CHECK_ROOT/pending" ]; then
    mv "$CALENDAR_CHECK_ROOT/pending" "$CALENDAR_CHECK_ROOT/modules"
fi
''')
        result = self.run_preview("managed-sleep")
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["sleep-1"])
        self.assertFalse((self.root/"restore").exists())

    def test_managed_sleep_waits_for_blanket_to_finish_unloading(self):
        self.mock_renderer("splash screensaver")
        get_prop = self.bin/"lipc-get-prop"
        get_prop.write_text(get_prop.read_text().replace(
            'cat "$CALENDAR_CHECK_ROOT/modules" ;;',
            '''cat "$CALENDAR_CHECK_ROOT/modules"
if [ -f "$CALENDAR_CHECK_ROOT/pending" ]; then
    mv "$CALENDAR_CHECK_ROOT/pending" "$CALENDAR_CHECK_ROOT/modules"
fi ;;
''',
        ))
        set_prop = self.bin/"lipc-set-prop"
        set_prop.write_text(set_prop.read_text().replace(
            'unload) echo splash > "$CALENDAR_CHECK_ROOT/modules"',
            'unload) echo splash > "$CALENDAR_CHECK_ROOT/pending"',
        ))
        result = self.run_preview("managed-sleep")
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["unload", "sleep-1", "draw", "load"])

    def test_sleep_preview_draws_once_and_exits_without_redrawing_stock(self):
        self.mock_sleep_transition("readyToSuspend")
        result = self.run_preview("sleep")
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["draw"])
        self.assertIn("IMAGE_REFRESH_CONFIRMED=1", (self.root/"sleep-preview.log").read_text())

    def test_sleep_preview_skips_draw_if_reader_has_resumed(self):
        self.mock_sleep_transition("active")
        self.assertNotEqual(self.run_preview("sleep").returncode, 0)
        self.assertFalse((self.root/"calls").exists())

    def test_success_draws_once_and_requests_redraw_after_delay(self):
        result = self.run_preview()
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        self.assertEqual((self.root/"calls").read_text().splitlines(), ["restore", "sleep-2", "draw", "sleep-25", "restore"])
        log = (self.root/"preview-v2.log").read_text()
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
        log = (self.root/"preview-v2.log").read_text()
        self.assertIn("FBInk build has no image support", log)
        self.assertIn("EXIT_STATUS=1", log)

    def test_fbink_init_failure_is_logged_and_aborts_before_draw(self):
        self.env["TEST_INIT_FAILURE"] = "139"
        self.assertNotEqual(self.run_preview().returncode, 0)
        self.assertFalse((self.root/"calls").exists())
        log = (self.root/"preview-v2.log").read_text()
        self.assertIn("FBINK_INIT_BEGIN=1", log)
        self.assertIn("FBInk framebuffer initialization failed", log)

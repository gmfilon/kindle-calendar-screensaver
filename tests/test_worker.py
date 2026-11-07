"""Run the actual POSIX worker against an isolated backend and clock.

On macOS missing Linux utilities are small Python test adapters. Linux CI uses
native flock/timeout/sha256sum; no test command touches LIPC or a framebuffer.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

WORKER = Path(__file__).resolve().parents[1]/"device"/"calendar-worker.sh"


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root/"calendar with spaces"
        self.bin = self.root/"bin"
        self.bin.mkdir()
        (self.base/"images").mkdir(parents=True)
        (self.base/"state").mkdir()
        self.env = dict(os.environ, PATH=str(self.bin)+os.pathsep+os.environ["PATH"],
                        TEST_DAY="2026-11-06", TEST_ROOT=str(self.base))
        self.script("date", "#!/bin/sh\nprintf '%s\\n' \"$TEST_DAY\"\n")
        if not shutil.which("flock"):
            self.script("flock", f"#!{sys.executable}\nimport fcntl, sys\n"
                        "try: fcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
                        "except BlockingIOError: sys.exit(1)\n")
        if not shutil.which("timeout"):
            self.script("timeout", f"#!{sys.executable}\nimport subprocess, sys\n"
                        "args = sys.argv[3:] if sys.argv[1] == '-k' else sys.argv[1:]\n"
                        "try: sys.exit(subprocess.run(args[1:], timeout=float(args[0])).returncode)\n"
                        "except subprocess.TimeoutExpired: sys.exit(124)\n")
        if not shutil.which("sha256sum"):
            self.script("sha256sum", f"#!{sys.executable}\nimport hashlib, pathlib, sys\n"
                        "print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest(), sys.argv[1])\n")
        self.add_image("2026-11-06")
        (self.base/"mode").write_text("asleep")
        (self.base/"failures").write_text("0")
        backend = self.base/"backend"
        backend.write_text('''#!/bin/sh
set -eu
case "$1" in
status) cat "$TEST_ROOT/mode" ;;
render)
  n=0
  [ ! -f "$TEST_ROOT/count" ] || n=$(cat "$TEST_ROOT/count")
  n=$((n + 1))
  echo "$n" > "$TEST_ROOT/count"
  [ ! -e "$TEST_ROOT/become-active" ] || echo active > "$TEST_ROOT/mode"
  [ "$n" -gt "$(cat "$TEST_ROOT/failures")" ] || exit 1
  printf '%s\\n' "$2" > "$TEST_ROOT/rendered"
  ;;
*) exit 1 ;;
esac
''')
        backend.chmod(0o755)

    def script(self, name, text):
        path = self.bin/name
        path.write_text(text)
        path.chmod(0o755)

    def add_image(self, day):
        data = b"test-fixture-image"
        (self.base/"images"/(day+".png")).write_bytes(data)
        with (self.base/"images"/"SHA256SUMS").open("a") as file:
            file.write(f"{hashlib.sha256(data).hexdigest()}  {day}.png\n")

    def run_worker(self, event="midnight"):
        return subprocess.run(["sh", str(WORKER), str(self.base), event], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_current_day_after_multiple_missed_days_and_clock_rollback(self):
        self.assertEqual(self.run_worker().returncode, 0)
        self.add_image("2027-01-03")
        self.env["TEST_DAY"] = "2027-01-03"
        self.assertEqual(self.run_worker().returncode, 0)
        self.assertEqual((self.base/"state"/"displayed").read_text().strip(), "2027-01-03")
        self.env["TEST_DAY"] = "2026-11-06"
        self.assertEqual(self.run_worker("sleep").returncode, 0)
        self.assertEqual((self.base/"state"/"displayed").read_text().strip(), "2026-11-06")

    def test_retries_commit_only_on_success(self):
        (self.base/"failures").write_text("2")
        self.assertEqual(self.run_worker().returncode, 0)
        self.assertEqual((self.base/"count").read_text().strip(), "3")
        (self.base/"failures").write_text("99")
        (self.base/"state"/"displayed").write_text("old-ack\n")
        self.assertEqual(self.run_worker().returncode, 74)
        self.assertEqual((self.base/"state"/"displayed").read_text(), "old-ack\n")
        self.assertEqual((self.base/"count").read_text().strip(), "6")

    def test_never_draw_while_reading_or_after_unlock_during_retry(self):
        (self.base/"mode").write_text("active")
        self.assertEqual(self.run_worker().returncode, 0)
        self.assertFalse((self.base/"count").exists())
        (self.base/"mode").write_text("asleep")
        (self.base/"failures").write_text("99")
        (self.base/"become-active").touch()
        self.assertEqual(self.run_worker().returncode, 0)
        self.assertEqual((self.base/"count").read_text().strip(), "1")
        self.assertFalse((self.base/"state"/"displayed").exists())

    def test_missing_corrupt_disabled_unknown(self):
        (self.base/"DISABLED").touch()
        self.assertEqual(self.run_worker().returncode, 78)
        (self.base/"DISABLED").unlink()
        self.env["TEST_DAY"] = "2026-11-07"
        self.assertEqual(self.run_worker().returncode, 66)
        self.env["TEST_DAY"] = "2026-11-06"
        (self.base/"mode").write_text("unknown")
        self.assertEqual(self.run_worker().returncode, 69)
        (self.base/"images"/"2026-11-06.png").write_bytes(b"corrupt")
        self.assertEqual(self.run_worker().returncode, 65)
        self.assertFalse((self.base/"count").exists())

    def test_exclusive_lock_and_release_after_process_exits(self):
        import fcntl
        with (self.base/"state"/"lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.assertEqual(self.run_worker().returncode, 75)
        self.assertEqual(self.run_worker().returncode, 0)

    def test_backend_timeout_is_bounded(self):
        (self.base/"backend").write_text(f"#!{sys.executable}\nimport signal, time\n"
                                        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(30)\n")
        self.assertEqual(self.run_worker().returncode, 69)
        self.assertFalse((self.base/"state"/"displayed").exists())

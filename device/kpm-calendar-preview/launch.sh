#!/bin/sh
# One-shot visual test. No renderer changes, powerd setters, RTC or autostart.
set -eu
umask 077
ROOT=${CALENDAR_CHECK_ROOT:-/mnt/us/kindle-calendar-check}
FBINK=${CALENDAR_FBINK:-/var/local/kmc/bin/fbink}
FB_SYS=${CALENDAR_SYSFS_FB0:-/sys/class/graphics/fb0}
EXPECTED=d9a19871727db0bbdb0c26058d0faf841ddee1f50af1660c1cc49d45800447cf

die() { echo "Calendar preview: $*"; exit 1; }
[ -r "$ROOT/OWNER.txt" ] && grep -qx 'kindle-calendar-check-v1' "$ROOT/OWNER.txt" || die 'owner marker mismatch'
command -v flock >/dev/null || die 'flock missing'
command -v timeout >/dev/null || die 'timeout missing'
command -v sha256sum >/dev/null || die 'sha256sum missing'
XREFRESH=$(command -v xrefresh) || die 'xrefresh missing; no image drawn'
[ -x "$FBINK" ] || die 'FBInk missing'
exec 9>"$ROOT/preview.lock"
flock -n 9 || die 'another preview is running'
exec 3>"$ROOT/preview.log"
DREW=0
cleanup() {
    result=$?
    trap - EXIT INT TERM
    if [ "$DREW" -eq 1 ]; then
        if DISPLAY=:0 timeout -k 2 5 "$XREFRESH" >&3 2>&1; then
            echo 'UI_REDRAW_REQUESTED=1' >&3
        else
            echo 'UI_REDRAW_FAILED=1' >&3
            result=1
        fi
    fi
    echo "EXIT_STATUS=$result" >&3
    exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
echo 'Calendar bounded visual test v1' >&3
ACTUAL=$(sha256sum "$ROOT/calendar-test.png")
ACTUAL=${ACTUAL%% *}
[ "$ACTUAL" = "$EXPECTED" ] || die 'sample checksum mismatch; no image drawn'
[ "$(cat "$FB_SYS/virtual_size")" = '1272,3392' ] || die 'framebuffer geometry changed; no image drawn'
[ "$(cat "$FB_SYS/bits_per_pixel")" = '8' ] || die 'framebuffer depth changed; no image drawn'
[ "$(cat "$FB_SYS/rotate")" = '0' ] || die 'framebuffer rotation changed; no image drawn'
HELP=$(timeout -k 2 5 "$FBINK" --help) || die 'FBInk help failed'
printf '%s\n' "$HELP" >&3
printf '%s\n' "$HELP" | grep -q 'Image=Yes' || die 'FBInk build has no image support; no image drawn'
timeout -k 2 5 "$FBINK" -e >&3 2>&1 || die 'FBInk framebuffer initialization failed'
DISPLAY=:0 timeout -k 2 5 "$XREFRESH" >&3 2>&1 || die 'UI redraw preflight failed; no image drawn'
echo 'UI_REDRAW_PREFLIGHT=1' >&3
echo 'La prueba del calendario comenzara en dos segundos.'
sleep 2
DREW=1
timeout -k 2 15 "$FBINK" -f -w -W GC16 -i "$ROOT/calendar-test.png" >&3 2>&1 || die 'image refresh failed'
echo 'IMAGE_REFRESH_CONFIRMED=1' >&3
# This short inspection delay is only for the manual visual test, not a scheduler.
sleep 25

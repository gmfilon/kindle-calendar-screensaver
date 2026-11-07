#!/bin/sh
# One-shot worker. An external, validated scheduler must hold the suspend guard.
# No powerd writes, framebuffer writes or daemon startup happen in this script.
set -eu
umask 077
BASE=${1:?Usage: calendar-worker.sh INSTALL_ROOT EVENT}
EVENT=${2:?Expected startup, sleep, midnight or resume}
case "$EVENT" in startup|sleep|midnight|resume) ;; *) exit 64 ;; esac
[ ! -e "$BASE/DISABLED" ] || { echo 'Calendar disabled' >&2; exit 78; }
[ -x "$BASE/backend" ] || { echo 'Validated backend missing' >&2; exit 78; }
command -v flock >/dev/null || { echo 'flock required' >&2; exit 69; }
command -v sha256sum >/dev/null || { echo 'sha256sum required' >&2; exit 69; }
command -v timeout >/dev/null || { echo 'timeout required' >&2; exit 69; }
[ -d "$BASE/state" ] || { echo 'state directory required' >&2; exit 78; }
# Kernel releases lock on crash/reboot. State lives on writable user storage.
exec 9>"$BASE/state/lock"
flock -n 9 || exit 75
# POSIX fallback for current Buenos Aires civil rules, not a general IANA TZ DB.
# Revalidate if Argentina changes its rules; do not alter Amazon's system clock.
export TZ=ART3
DAY=$(date +%F)
IMAGE="$BASE/images/$DAY.png"
[ -f "$IMAGE" ] && [ ! -L "$IMAGE" ] || { echo "Missing image: $DAY" >&2; exit 66; }
EXPECTED=$(awk -v name="$DAY.png" '$2 == name {print $1}' "$BASE/images/SHA256SUMS")
ACTUAL=$(sha256sum "$IMAGE")
ACTUAL=${ACTUAL%% *}
[ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] || { echo 'Image checksum mismatch' >&2; exit 65; }
ATTEMPT=1
while [ "$ATTEMPT" -le 3 ]; do
    # backend status must mean it owns the sleeping screen, not merely powerd idle.
    STATUS=$(timeout -k 1 5 "$BASE/backend" status) || exit 69
    case "$STATUS" in
        active) exit 0 ;;
        asleep) ;;
        *) echo 'Unknown screen ownership' >&2; exit 69 ;;
    esac
    # A retry across midnight must not render yesterday's calendar.
    [ "$(date +%F)" = "$DAY" ] || exit 75
    # render must itself recheck ownership and have a bounded execution time.
    if timeout -k 1 10 "$BASE/backend" render "$IMAGE"; then
        printf '%s\n' "$DAY" > "$BASE/state/displayed.tmp"
        mv "$BASE/state/displayed.tmp" "$BASE/state/displayed"
        exit 0
    fi
    ATTEMPT=$((ATTEMPT + 1))
done
echo 'Display failed after 3 attempts; prior acknowledgment preserved' >&2
exit 74

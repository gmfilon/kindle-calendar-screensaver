#!/bin/sh
# One-shot visual tests. Managed modes temporarily pause the stock renderer.
set -eu
umask 077
ROOT=${CALENDAR_CHECK_ROOT:-/mnt/us/kindle-calendar-check}
FBINK=${CALENDAR_FBINK:-/var/local/kmc/bin/fbink}
FB_SYS=${CALENDAR_SYSFS_FB0:-/sys/class/graphics/fb0}
EXPECTED=d9a19871727db0bbdb0c26058d0faf841ddee1f50af1660c1cc49d45800447cf
IMAGE="$ROOT/calendar-test.png"
MODE=${1:-active}
POWERD=com.lab126.powerd
BLANKET=com.lab126.blanket
RESTORE=${CALENDAR_SCREEN_RESTORE:-/tmp/kindle-calendar-screen-restore}
SHIELD_EXPECTED=0d3661b6a5102eb268474d2ad52d9f89ed69eb60f163e1630eea4b315ef99f47
MANAGED=0
SHIELDED=0
DATED=0
ENTER_EVENT=readyToSuspend
ENTER_STATE=readyToSuspend
WAKE_WAIT=45
SHIELD_LIMIT=85

die() { echo "Calendar preview: $*" >&2; exit 1; }
case "$MODE" in
    active) LOG=preview-v2.log ;;
    sleep) LOG=sleep-preview.log ;;
    managed-sleep) LOG=managed-sleep-preview.log; MANAGED=1 ;;
    shield-sleep) LOG=shield-sleep-preview.log; MANAGED=1; SHIELDED=1 ;;
    quick-sleep|dated-sleep)
        LOG=quick-sleep-v2.log
        MANAGED=1
        SHIELDED=1
        ENTER_EVENT=goingToScreenSaver
        ENTER_STATE=screenSaver
        WAKE_WAIT=135
        SHIELD_LIMIT=175
        if [ "$MODE" = dated-sleep ]; then
            LOG=dated-sleep.log
            DATED=1
        fi
        ;;
    *) die 'unknown preview mode' ;;
esac
[ -r "$ROOT/OWNER.txt" ] && grep -qx 'kindle-calendar-check-v1' "$ROOT/OWNER.txt" || die 'owner marker mismatch'
exec 9>"$ROOT/preview.lock"
if ! flock -n 9 2>>"$ROOT/$LOG"; then
    echo 'Calendar preview: could not acquire preview lock' >>"$ROOT/$LOG"
    exit 1
fi
exec 3>"$ROOT/$LOG"
exec 2>&3

prop() {
    timeout -k 2 3 lipc-get-prop "$POWERD" "$1"
}

is_sleep_screen() {
    state=$(prop state) || return 1
    [ "$state" = "$ENTER_STATE" ] || [ "$state" = readyToSuspend ]
}

blanket_modules() {
    timeout -k 2 3 lipc-get-prop "$BLANKET" load
}

has_module() {
    printf '%s\n' "$1" | tr '[:space:]' '\n' | grep -qx "$2"
}

wait_for_stock() {
    wanted=$1
    # Blanket can acknowledge load and unload before changing its module list.
    for delay in 0 1 1 2; do
        [ "$delay" -eq 0 ] || sleep "$delay"
        modules=$(blanket_modules) || continue
        current=absent
        if has_module "$modules" screensaver; then
            current=present
        fi
        [ "$current" != "$wanted" ] || return 0
    done
    return 1
}

restore_stock() {
    if ! { [ -f "$RESTORE" ] && [ ! -L "$RESTORE" ] && grep -qx screensaver "$RESTORE"; }; then
        echo 'RESTORE_ERROR=invalid recovery marker' >&3
        return 1
    fi
    if ! modules=$(blanket_modules); then
        echo 'RESTORE_ERROR=could not query Blanket' >&3
        return 1
    fi
    printf 'RESTORE_MODULES_BEFORE=%s\n' "$modules" >&3
    if ! has_module "$modules" screensaver; then
        timeout -k 2 3 lipc-set-prop "$BLANKET" load screensaver >&3 ||
            echo 'RESTORE_LOAD_REQUEST_FAILED=1' >&3
        if ! wait_for_stock present; then
            printf 'RESTORE_MODULES_AFTER=%s\n' "$modules" >&3
            echo 'RESTORE_ERROR=module not confirmed after load' >&3
            return 1
        fi
        printf 'RESTORE_MODULES_AFTER=%s\n' "$modules" >&3
    fi
    rm -f "$RESTORE" || return 1
    echo 'STOCK_RENDERER_RESTORED=1' >&3
}

check_stock_only() {
    modules=$(blanket_modules) || die 'could not read stock renderer state'
    printf 'BLANKET_MODULES=%s\n' "$modules" >&3
    has_module "$modules" screensaver || die 'standard screensaver module not loaded'
    if has_module "$modules" ad_screensaver; then
        die 'ad renderer also loaded; leaving renderer state unchanged'
    fi
}

check_geometry() {
    [ "$(cat "$FB_SYS/virtual_size")" = '1272,3392' ] || die 'framebuffer geometry changed; no image drawn'
    [ "$(cat "$FB_SYS/bits_per_pixel")" = '8' ] || die 'framebuffer depth changed; no image drawn'
    [ "$(cat "$FB_SYS/rotate")" = '0' ] || die 'framebuffer rotation changed; no image drawn'
}

check_image() {
    [ -f "$IMAGE" ] && [ ! -L "$IMAGE" ] || die 'calendar image missing'
    actual=$(sha256sum "$IMAGE") || die 'could not verify calendar image'
    [ "${actual%% *}" = "$EXPECTED" ] || die 'calendar checksum mismatch; no image drawn'
}

calendar_day() {
    TZ=ART3 date +%F
}

select_dated_image() {
    DAY=$(calendar_day) || die 'could not read local date'
    case "$DAY" in
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
        *) die 'unexpected local date format' ;;
    esac
    filename="$DAY.png"
    IMAGE="$IMAGE_DIR/$filename"
    EXPECTED=$(awk -v name="$filename" '
        $2 == name { hash = $1; count++ }
        END { if (count == 1) print hash; else exit 1 }
    ' "$IMAGE_DIR/SHA256SUMS") || die "no unique checksum for $DAY"
    check_image
    printf 'CALENDAR_DAY=%s\n' "$DAY" >&3
}

signal_shield() {
    [ -s "$SHIELD_DIR/pid" ] || return 1
    shield_pid=$(cat "$SHIELD_DIR/pid") || return 1
    case "$shield_pid" in ''|*[!0-9]*) return 1 ;; esac
    [ "$(readlink "/proc/$shield_pid/exe")" = "$SHIELD" ] || return 1
    kill "-$1" "$shield_pid"
}

start_shield() {
    SHIELD_DIR=$(mktemp -d /tmp/kindle-calendar-shield.XXXXXX) || die 'could not create shield work directory'
    DISPLAY=:0 timeout -k 2 "$SHIELD_LIMIT" /bin/sh -c '
        printf "%s\n" "$$" >"$1" || exit 1
        exec "$2"
    ' shield "$SHIELD_DIR/pid" "$SHIELD" >"$SHIELD_DIR/log" 2>&1 9>&- &
    SHIELD_RUNNER=$!
    for attempt in 1 2 3; do
        if grep -q '^screensaver_shield: active,' "$SHIELD_DIR/log" && signal_shield 0; then
            echo 'SHIELD_READY=1' >&3
            return 0
        fi
        sleep 1
    done
    die 'shield did not become ready'
}

stop_shield() {
    [ -n "$SHIELD_DIR" ] || return 0
    if [ -n "$SHIELD_RUNNER" ]; then
        signal_shield TERM || kill -TERM "$SHIELD_RUNNER" 2>/dev/null || :
        wait "$SHIELD_RUNNER" || :
    fi
    cat "$SHIELD_DIR/log" >&3 || :
    rm -f "$SHIELD_DIR/pid" "$SHIELD_DIR/log"
    rmdir "$SHIELD_DIR"
}

DREW=0
RESTORE_NEEDED=0
SHIELD_DIR=''
SHIELD_RUNNER=''
cleanup() {
    result=$?
    trap - EXIT HUP INT TERM
    if ! stop_shield; then
        echo 'SHIELD_CLEANUP_FAILED=1' >&3
        result=1
    fi
    if [ "$RESTORE_NEEDED" -eq 1 ] && ! restore_stock; then
        echo 'STOCK_RENDERER_RESTORE_FAILED=1' >&3
        result=1
    fi
    if [ "$DREW" -eq 1 ] || [ -n "$SHIELD_RUNNER" ]; then
        if DISPLAY=:0 timeout -k 2 5 "$XREFRESH" >&3; then
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
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
echo 'Calendar bounded visual test v2' >&3
if [ "$MANAGED" -eq 1 ] && { [ -e "$RESTORE" ] || [ -L "$RESTORE" ]; }; then
    restore_stock || die 'stock renderer recovery failed'
    exit 0
fi
ulimit -c 0
command -v timeout >/dev/null || die 'timeout missing'
command -v sha256sum >/dev/null || die 'sha256sum missing'
XREFRESH=$(command -v xrefresh) || XREFRESH=''
printf 'XREFRESH=%s\n' "${XREFRESH:-missing}" >&3
[ -x "$FBINK" ] || die 'FBInk missing'
if [ "$DATED" -eq 1 ]; then
    IMAGE_DIR="$(dirname "$0")/images"
    select_dated_image
else
    check_image
fi
check_geometry
HELP=$(timeout -k 2 5 "$FBINK" --help) || die 'FBInk help failed'
printf '%s\n' "$HELP" | sed -n '1,4p' >&3
printf '%s\n' "$HELP" | grep -q 'Image=Yes' || die 'FBInk build has no image support; no image drawn'
[ -n "$XREFRESH" ] || die 'xrefresh missing; no image drawn'
echo 'FBINK_INIT_BEGIN=1' >&3
# FBInk initializes before reading stdin. EOF leaves the framebuffer untouched.
# The Kindle build crashed with -e, which also calls the state formatter.
timeout -k 2 5 "$FBINK" -v </dev/null >&3 || die 'FBInk framebuffer initialization failed'
echo 'FBINK_INIT_OK=1' >&3

if [ "$MODE" != active ]; then
    [ "$(prop isCharging)" = 0 ] || die 'unplug USB before the sleep test'
    [ "$(prop state)" = active ] || die 'launch the sleep test from the active library'
    if [ "$MANAGED" -eq 1 ]; then
        check_stock_only
    fi
    if [ "$SHIELDED" -eq 1 ]; then
        SHIELD=$(readlink -f "$(dirname "$0")/screensaver_shield") || die 'shield binary missing'
        actual_shield=$(sha256sum "$SHIELD") || die 'could not verify shield binary'
        [ "${actual_shield%% *}" = "$SHIELD_EXPECTED" ] || die 'shield checksum mismatch'
        chmod 700 "$SHIELD" || die 'could not make shield executable'
        timeout -k 2 5 /lib/ld-linux-armhf.so.3 --list "$SHIELD" >&3 ||
            die 'shield dependencies missing'
    fi
    printf 'PREVENT_SCREEN_SAVER=%s\n' "$(prop preventScreenSaver || echo unavailable)" >&3
    printf 'WAITING_FOR_EVENT=%s\n' "$ENTER_EVENT" >&3
    timeout -k 2 145 lipc-wait-event -s 140 "$POWERD" "$ENTER_EVENT" >&3 ||
        die 'sleep entry event not observed'
    printf 'SLEEP_EVENT_EPOCH=%s\n' "$(date +%s)" >&3
    if [ "$DATED" -eq 1 ]; then
        select_dated_image
    fi
    check_geometry
    [ "$(prop isCharging)" = 0 ] || die 'USB was connected during the test'
    if [ "$ENTER_STATE" = screenSaver ] && ! is_sleep_screen; then
        # The entry notification can precede publication of the new state.
        sleep 1
    fi
    is_sleep_screen || die 'powerd is outside the sleep screen'
    if [ "$MANAGED" -eq 1 ]; then
        check_stock_only
        (set -C; printf 'screensaver\n' >"$RESTORE") || die 'could not save recovery marker'
        RESTORE_NEEDED=1
        timeout -k 2 3 lipc-set-prop "$BLANKET" unload screensaver >&3 ||
            die 'could not pause stock renderer'
        wait_for_stock absent || die 'stock renderer remains loaded'
        printf 'BLANKET_MODULES_AFTER_UNLOAD=%s\n' "$modules" >&3
        if has_module "$modules" ad_screensaver; then
            die 'ad renderer loaded during test'
        fi
        if [ "$SHIELDED" -eq 1 ]; then
            is_sleep_screen || die 'powerd left the sleep screen'
            start_shield
        fi
        is_sleep_screen || die 'powerd left the sleep screen'
    fi
    if [ "$DATED" -eq 1 ] && [ "$(calendar_day)" != "$DAY" ]; then
        die 'local date changed during the display setup'
    fi
    is_sleep_screen || die 'powerd left the sleep screen'
    echo 'SLEEP_DRAW_BEGIN=1' >&3
    timeout -k 2 5 "$FBINK" -f -w -W GC16 -i "$IMAGE" >&3 ||
        die 'sleep image refresh failed'
    echo 'IMAGE_REFRESH_CONFIRMED=1' >&3
    printf 'DRAW_COMPLETE_EPOCH=%s\n' "$(date +%s)" >&3
    if [ "$MANAGED" -eq 1 ] && is_sleep_screen; then
        if event=$(timeout -k 2 "$((WAKE_WAIT + 3))" lipc-wait-event -s "$WAKE_WAIT" "$POWERD" outOfScreenSaver,goingToPasswdDlg); then
            printf 'WAKE_EVENT=%s\n' "$event" >&3
            case "$event" in
                goingToPasswdDlg*)
                    if [ "$SHIELDED" -eq 1 ]; then
                        signal_shield USR1 || die 'could not put shield behind PIN dialog'
                        timeout -k 2 32 lipc-wait-event -s 30 "$POWERD" outOfScreenSaver >&3 ||
                            echo 'UNLOCK_EVENT_NOT_OBSERVED=1' >&3
                    fi
                    ;;
            esac
        else
            echo 'WAKE_EVENT_NOT_OBSERVED=1' >&3
        fi
    fi
    exit 0
fi

DISPLAY=:0 timeout -k 2 5 "$XREFRESH" >&3 || die 'UI redraw preflight failed; no image drawn'
echo 'UI_REDRAW_PREFLIGHT=1' >&3
echo 'La prueba del calendario comenzara en dos segundos.'
sleep 2
DREW=1
echo 'FBINK_DRAW_BEGIN=1' >&3
timeout -k 2 15 "$FBINK" -f -w -W GC16 -i "$IMAGE" >&3 || die 'image refresh failed'
echo 'IMAGE_REFRESH_CONFIRMED=1' >&3
# This short inspection delay is only for the manual visual test, not a scheduler.
sleep 25

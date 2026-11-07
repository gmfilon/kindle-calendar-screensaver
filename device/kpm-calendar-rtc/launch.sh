#!/bin/sh
# Read-only inspection by default. Use 'trial' or 'named-trial' for one alarm.
set -eu
umask 077
ROOT=${CALENDAR_CHECK_ROOT:-/mnt/us/kindle-calendar-check}
POWERD=com.lab126.powerd
ALARM_SECONDS=180

[ -r "$ROOT/OWNER.txt" ] && grep -qx 'kindle-calendar-check-v1' "$ROOT/OWNER.txt" || exit 1
case "${1:-inspect}" in
inspect)
    exec >"$ROOT/power-inspection.log" 2>&1
    echo 'Calendar power inspection v1'
    for node in /sys/class/rtc/rtc*/name /sys/class/rtc/rtc*/wakealarm \
        /sys/class/rtc/rtc*/device/power/wakeup; do
        if [ -r "$node" ]; then
            printf '%s=%s\n' "$node" "$(cat "$node" || :)"
        fi
    done
    grep -Ei 'alrm|alarm' /proc/driver/rtc || :
    if [ -r /var/log/messages ]; then
        tail -n 5000 /var/log/messages | grep -Ei 'powerd.*(rtc|alarm|suspend|resume)' | tail -n 80
    fi
    dmesg | grep -Ei 'PM: suspend (entry|exit)|bd70528-rtc|wakeup irq' | tail -n 30
    pid=$(pidof powerd || :)
    case "$pid" in
        ''|*[!0-9]*) ;;
        *) timeout -k 2 5 strings "/proc/$pid/exe" |
            grep -Ei 'rtcWakeup|wakealarm|alarmtimer|rtc.*(alarm|fail)|wake.*timer' | head -n 60 ;;
    esac
    echo 'INSPECTION_COMPLETE=1'
    exit 0
    ;;
trial|named-trial) ;;
*) exit 64 ;;
esac
exec 9>"$ROOT/rtc-test.lock"
flock -n 9 || exit 1
if [ "$1" = named-trial ]; then
    exec >"$ROOT/rtc-test-named.log" 2>&1
else
    exec >"$ROOT/rtc-test-v2.log" 2>&1
fi

trap 'printf "EXIT_STATUS=%s\n" "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
fail() { printf 'ERROR=%s\n' "$1"; exit 1; }

prop() {
    timeout -k 2 5 lipc-get-prop "$POWERD" "$1"
}

snapshot() {
    printf 'SNAPSHOT=%s EPOCH=%s\n' "$1" "$(date +%s)"
    for node in /sys/power/mem_sleep /sys/power/suspend_stats/success \
        /sys/power/suspend_stats/fail /sys/power/pm_wakeup_irq \
        /sys/class/rtc/rtc0/wakealarm; do
        if [ -r "$node" ]; then
            printf '%s=%s\n' "$node" "$(cat "$node" || :)"
        fi
    done
    if [ -r /proc/interrupts ]; then
        grep -iE 'rtc|bd71828' /proc/interrupts || :
    fi
    if [ -r /proc/driver/rtc ]; then
        grep -E '^(rtc_time|rtc_date|alrm_time|alrm_date|alarm_IRQ|alrm_pending)' /proc/driver/rtc || :
    fi
}

printf 'TRIAL_MODE=%s\n' "$1"
[ "$(prop isCharging)" = 0 ] || fail 'unplug USB before launching the test'
snapshot START
echo 'WAITING_FOR_READY_TO_SUSPEND=1'
# Single-event mode on PW6 prints the payload without the subscribed name.
payload=$(timeout -k 2 245 lipc-wait-event -s 240 "$POWERD" readyToSuspend) ||
    fail 'no readyToSuspend event within the wait'
printf 'READY_PAYLOAD=%s\n' "$payload"

snapshot BEFORE_ALARM
armed_at=$(date +%s)
# Leave an already imminent kernel alarm alone. The path can be absent or
# empty on kernels where powerd manages the alarm through another interface.
if [ -r /sys/class/rtc/rtc0/wakealarm ]; then
    pending=$(cat /sys/class/rtc/rtc0/wakealarm)
    case "$pending" in
        ''|*[!0-9]*) ;;
        *) if [ "$pending" -gt "$armed_at" ] && [ "$pending" -le "$((armed_at + ALARM_SECONDS + 30))" ]; then
               fail 'another kernel alarm is already imminent'
           fi ;;
    esac
fi
[ "$(prop isCharging)" = 0 ] || fail 'USB was connected during the test'
state=$(prop state)
printf 'STATE_BEFORE_ALARM=%s\n' "$state"
[ "$state" = readyToSuspend ] || fail 'powerd left readyToSuspend'
armed_at=$(date +%s)
printf 'ALARM_REQUEST_EPOCH=%s DELAY_SECONDS=%s\n' "$armed_at" "$ALARM_SECONDS"
if [ "$1" = named-trial ]; then
    timeout -k 2 5 lipc-set-prop -s "$POWERD" rtcWakeup2 "kindle_calendar_trial:$ALARM_SECONDS" ||
        fail 'powerd rejected rtcWakeup2'
else
    timeout -k 2 5 lipc-set-prop -i "$POWERD" rtcWakeup "$ALARM_SECONDS" ||
        fail 'powerd rejected rtcWakeup'
fi
echo 'ALARM_ACCEPTED=1'
snapshot AFTER_REQUEST

if payload=$(timeout -k 2 220 lipc-wait-event -s 215 "$POWERD" wakeupFromSuspend); then
    printf 'WAKE_PAYLOAD=%s DELTA_SECONDS=%s\n' "$payload" "$(($(date +%s) - armed_at))"
else
    echo 'RESUME_EVENT_NOT_OBSERVED=1'
fi
snapshot AFTER_WAIT
printf 'FINAL_STATE=%s\n' "$(prop state)"
if [ -r /var/log/messages ]; then
    tail -n 5000 /var/log/messages |
        grep -Ei 'powerd.*(rtcset|rtc_set_ignored|setting rtc wakeup time|rtcclose|RTC Client)' |
        tail -n 40
fi

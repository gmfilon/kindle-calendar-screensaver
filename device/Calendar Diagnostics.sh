#!/bin/sh
# Manual, one-shot diagnostics for the approved hardware validation phase.
# Reads system information; writes only its own report in user storage.
set -u
umask 077
ROOT=/mnt/us/kindle-calendar-check
if [ ! -r "$ROOT/OWNER.txt" ] || ! grep -qx 'kindle-calendar-check-v1' "$ROOT/OWNER.txt"; then
    echo 'Calendar diagnostic folder is missing or has an unexpected owner marker.'
    exit 1
fi
if [ ! -r "$ROOT/probe.sh" ]; then
    echo 'Calendar probe is missing.'
    exit 1
fi
{
    echo 'Kindle Calendar diagnostic report v1'
    printf '\n== privileges ==\n'
    id -u
    printf '\n== clock (read only) ==\n'
    date '+%Y-%m-%d %H:%M:%S %z %Z'
    printf '\n== user storage ==\n'
    df -k "$ROOT"
    sh "$ROOT/probe.sh"
    printf '\n== optional installed display tools ==\n'
    command -v fbink || :
    ls -l /var/local/kmc/bin/fbink* /usr/bin/fbink* 2>/dev/null || :
    printf '\n== sample image checksum ==\n'
    if command -v sha256sum >/dev/null; then
        sha256sum "$ROOT/calendar-test.png"
    fi
    printf '\n== end of report ==\n'
} > "$ROOT/probe.txt.tmp" 2>&1
mv "$ROOT/probe.txt.tmp" "$ROOT/probe.txt"
echo 'Diagnostico terminado. Volve a la biblioteca y conecta el Kindle a la Mac.'
echo 'Reporte: kindle-calendar-check/probe.txt'

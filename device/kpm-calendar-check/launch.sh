#!/bin/sh
# Local diagnostic launcher. KPM runs this via /bin/sh; no network or daemon.
set -eu
SCRIPT='/mnt/us/documents/Calendar Diagnostics.sh'
if [ ! -r "$SCRIPT" ]; then
    echo 'Calendar diagnostic script is missing.'
    exit 1
fi
exec /bin/sh "$SCRIPT"

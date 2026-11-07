#!/bin/sh
# Read-only evidence collection AFTER an independently approved jailbreak.
# No serial numbers, account data, network access or setters.
set -u
printf '\n== kernel ==\n'
uname -srm
printf '\n== firmware ==\n'
[ ! -r /etc/prettyversion.txt ] || cat /etc/prettyversion.txt
printf '\n== ABI ==\n'
ls -l /lib/ld-linux*.so* 2>/dev/null || :
printf '\n== tools ==\n'
for tool in lipc-get-prop lipc-probe lipc-wait-event lipc-set-prop flock sha256sum timeout; do
    command -v "$tool" || :
done
printf '\n== framebuffer ==\n'
for name in virtual_size bits_per_pixel rotate; do
    [ ! -r "/sys/class/graphics/fb0/$name" ] || cat "/sys/class/graphics/fb0/$name"
done
printf '\n== RTC device availability (not proof of wake) ==\n'
ls -ld /sys/class/rtc/rtc* /dev/rtc* 2>/dev/null || :
printf '\n== powerd properties ==\n'
if command -v lipc-probe >/dev/null; then
    lipc-probe com.lab126.powerd 2>&1 || :
fi

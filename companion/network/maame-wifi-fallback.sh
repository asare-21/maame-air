#!/bin/bash
# Start the Maame hotspot when no known Wi-Fi network connects within WAIT_S of boot.
# Known networks are ordinary NetworkManager profiles (autoconnect=yes); the
# hotspot profile "maame-hotspot" has autoconnect=no and is only used here.
# shortcut: checks once at boot only; a known network that appears later needs a reboot (or: nmcli con up <name>).
WAIT_S="${MAAME_WIFI_WAIT_S:-60}"
HOTSPOT=maame-hotspot

wlan_connection() {
    nmcli -t -f NAME,DEVICE con show --active | awk -F: '$2=="wlan0"{print $1}'
}

for ((waited = 0; waited < WAIT_S; waited += 5)); do
    active="$(wlan_connection)"
    if [ -n "$active" ] && [ "$active" != "$HOTSPOT" ]; then
        echo "[wifi-fallback] on known network '$active'"
        exit 0
    fi
    sleep 5
done

echo "[wifi-fallback] no known network after ${WAIT_S}s, starting $HOTSPOT"
exec nmcli con up "$HOTSPOT"

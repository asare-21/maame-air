#!/bin/bash
# Create (or recreate) the Maame fallback hotspot profile on the Pi. Run with sudo.
# OPEN network (no password): anyone in range can join and reach MAVLink on
# UDP 14550 / TCP 5760, so enable MAVLink signing before field use.
# (WPA2 on the Pi Zero W's brcmfmac AP made phones report "wrong password".)
set -e
HOTSPOT=maame-hotspot
SSID="Maame-$(tail -c 5 /proc/device-tree/serial-number | tr -d '\0' | tr a-z A-Z)"

nmcli -t -f NAME con show | grep -qx "$HOTSPOT" && nmcli con delete "$HOTSPOT" >/dev/null
nmcli con add type wifi ifname wlan0 con-name "$HOTSPOT" autoconnect no ssid "$SSID" \
    802-11-wireless.mode ap 802-11-wireless.band bg ipv4.method shared >/dev/null
echo "hotspot '$HOTSPOT' (SSID $SSID, open, Pi at 10.42.0.1) ready; started by maame-wifi-fallback at boot"

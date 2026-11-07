#!/bin/bash
# 4G for MaameDrone: a USB LTE modem as a backup/long-range link, reached over
# Tailscale (private, encrypted, no port forwarding). Run on the Pi with sudo:
#   sudo ./install-4g.sh <APN>        e.g. sudo ./install-4g.sh everywhere
# Afterwards, in ArduDeck's Maame connect card, put the Pi's Tailscale address
# (shown at the end, 100.x.y.z or maame.<tailnet>.ts.net) in "4G address".
# MAVLink signing must be on before flying over 4G: the launch checklist enforces it.
set -euo pipefail
APN="${1:?usage: sudo ./install-4g.sh <APN of your SIM>}"

# 1. Modem: NetworkManager drives it through ModemManager.
apt-get install -y modemmanager
systemctl enable --now ModemManager
sleep 5
mmcli -L || { echo "no modem found: plug in the USB LTE modem and run again" >&2; exit 1; }
nmcli connection delete maame-lte >/dev/null 2>&1 || true
# metric 700: Wi-Fi (lower metric) stays the default route whenever it is up
nmcli connection add type gsm ifname '*' con-name maame-lte apn "$APN" \
    connection.autoconnect yes ipv4.route-metric 700 ipv6.route-metric 700
nmcli connection up maame-lte || echo "LTE not up yet (signal/SIM?); NetworkManager keeps retrying" >&2

# 2. Tailscale: the laptop reaches the Pi's router port 14550 at its tailnet address.
if ! command -v tailscale >/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
fi
tailscale up --hostname=maame --ssh=false
echo "Tailscale address for ArduDeck's '4G address': $(tailscale ip -4 | head -1)"

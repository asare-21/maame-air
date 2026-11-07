#!/bin/bash
# Install the MaameDrone phone dashboard on the Pi. From the Mac (repo root):
#   scp -r companion/dashboard maame@maame.local:~/
#   ssh -t maame@maame.local 'sudo bash ~/dashboard/install-dashboard.sh'
# It imports maame_ready from ~/startup-files (signing key loader).
# Creates a 6-digit PIN in /etc/maame/dashboard-pin (root, 600) if there is none
# and prints it once. Phone: http://maame.local:8080 (hotspot: http://10.42.0.1:8080).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST=/home/maame/dashboard

if [ "$HERE" != "$DEST" ]; then  # copied elsewhere: put the files where the service runs them
    install -d -o maame -g maame "$DEST"
    install -m 644 -o maame -g maame "$HERE/maame_dashboard.py" "$HERE/index.html" "$DEST/"
fi

install -d -m 700 /etc/maame
if [ ! -s /etc/maame/dashboard-pin ]; then
    umask 077
    n="$(od -An -N4 -tu4 /dev/urandom | tr -d ' ')"
    printf '%06d\n' "$((n % 1000000))" > /etc/maame/dashboard-pin
    chmod 600 /etc/maame/dashboard-pin
    echo "dashboard PIN: $(cat /etc/maame/dashboard-pin)  (shown once; sudo cat /etc/maame/dashboard-pin to see it again)"
fi

install -m 644 "$HERE/maame-dashboard.service" /etc/systemd/system/maame-dashboard.service
systemctl daemon-reload
systemctl enable --now maame-dashboard.service
sleep 3
systemctl --no-pager --lines=4 status maame-dashboard.service || true
echo "open http://$(hostname).local:8080 on a phone on the same network"

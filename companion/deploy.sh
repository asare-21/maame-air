#!/bin/bash
# Update the Maame Pi with this repo's companion software, from the Mac:
#   companion/deploy.sh                 # maame@maame.local
#   companion/deploy.sh maame@10.42.0.1 # over the Pi's hotspot
# Backs up the Pi's current files, copies the companion + dashboard code, compiles it
# on the Pi (nothing restarts if it does not compile), restarts the services that are
# already installed, and records which commit is running. New services (camera, 4G,
# dashboard first install) are still installed by hand with their install scripts.
set -euo pipefail
PI="${1:-maame@maame.local}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REV="$(git -C "$HERE" rev-parse --short HEAD)$(git -C "$HERE" diff --quiet -- . || echo -dirty)"
STAMP="$(date +%Y%m%d-%H%M%S)"
PY=/home/maame/drone-env/bin/python3
SSH_OPTS=(-o ConnectTimeout=10 -o ServerAliveInterval=5 -o ServerAliveCountMax=3)
ssh() { command ssh "${SSH_OPTS[@]}" "$@"; }
scp() { command scp "${SSH_OPTS[@]}" "$@"; }

echo "== deploying companion $REV to $PI"
# Restarting the companion in flight would stop the gate heartbeat (-> RTL): never while armed.
ssh "$PI" "$PY - <<'PYEOF'
import sys
from pymavlink import mavutil
m = mavutil.mavlink_connection('tcp:127.0.0.1:5760', source_system=233)
hb = None
for _ in range(20):
    hb = m.recv_match(type='HEARTBEAT', blocking=True, timeout=1)
    if hb and hb.get_srcComponent() == 1: break
    hb = None
if hb is None: print('no FC heartbeat: deploying anyway (FC off?)')
elif hb.base_mode & 128: sys.exit('the drone is ARMED: not deploying')
PYEOF"
ssh "$PI" "set -e; mkdir -p ~/startup-files/backup-$STAMP ~/dashboard
  cp ~/startup-files/*.py ~/startup-files/*.sh ~/startup-files/backup-$STAMP/ 2>/dev/null || true"
scp -q "$HERE"/startup-files/*.py "$HERE"/startup-files/start-maame.sh "$HERE"/startup-files/requirements.txt "$PI":startup-files/
scp -q "$HERE"/dashboard/maame_dashboard.py "$HERE"/dashboard/index.html "$PI":dashboard/

ssh "$PI" "set -e
  $PY -m pip install -q --disable-pip-version-check -r ~/startup-files/requirements.txt || echo 'pip install failed (Pi offline?): start-maame.sh retries at boot'
  cd ~/startup-files && $PY -m py_compile maame_*.py && cd ~/dashboard && $PY -m py_compile maame_dashboard.py
  echo '$REV $STAMP' > ~/startup-files/VERSION
  for s in maame-startup maame-dashboard; do
    if systemctl list-unit-files \"\$s.service\" >/dev/null 2>&1 && systemctl is-enabled --quiet \"\$s\"; then
      sudo -n systemctl restart \"\$s\" && echo \"restarted \$s\"
    fi
  done
  sleep 8
  for s in mavlink-router maame-startup maame-dashboard maame-camera; do
    printf '%-16s %s\n' \"\$s\" \"\$(systemctl is-active \$s 2>/dev/null || true)\"
  done
  echo \"running: \$(cat ~/startup-files/VERSION)  (backup: ~/startup-files/backup-$STAMP)\""

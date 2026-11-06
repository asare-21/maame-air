#!/bin/bash
# MaameDrone startup wrapper.
#  1. If the internet is reachable, pull the latest code from GitHub (fast-forward only).
#     If there's no network, the pull fails, or the new code doesn't compile, keep the onboard version.
#  2. Find the drone-env venv and run maame_startup.py (checks, LED test, live loop).
# Usage: ./start-maame.sh [--check-only] [--skip-led-test] [--no-update]
DIR="$(cd "$(dirname "$0")" && pwd)"
GIT_USER="${MAAME_GIT_USER:-maame}"   # owner of the clone; git refuses root on another user's repo
NET_WAIT_S="${MAAME_NET_WAIT_S:-20}"   # how long to wait for the network at boot
FETCH_TIMEOUT_S=30

log() { echo "[start-maame] $*"; }

as_owner() {
    if [ "$(id -u)" = 0 ] && id "$GIT_USER" >/dev/null 2>&1; then
        sudo -u "$GIT_USER" -H "$@"
    else
        "$@"
    fi
}

update_from_github() {
    local top branch before after
    top="$(as_owner git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)" || {
        log "$DIR is not a git clone, skipping update"; return; }
    branch="$(as_owner git -C "$top" rev-parse --abbrev-ref HEAD)"

    # wait briefly for the network (Wi-Fi can come up after this service starts)
    local waited=0
    until as_owner timeout 5 git -C "$top" ls-remote --exit-code origin HEAD >/dev/null 2>&1; do
        if [ "$waited" -ge "$NET_WAIT_S" ]; then
            log "GitHub not reachable, running onboard version $(as_owner git -C "$top" rev-parse --short HEAD)"
            return
        fi
        sleep 5; waited=$((waited + 5))
    done

    before="$(as_owner git -C "$top" rev-parse HEAD)"
    if ! as_owner timeout "$FETCH_TIMEOUT_S" git -C "$top" pull --ff-only --quiet origin "$branch"; then
        log "git pull failed (local changes or diverged branch?), running onboard version"
        return
    fi
    after="$(as_owner git -C "$top" rev-parse HEAD)"
    if [ "$before" = "$after" ]; then
        log "already up to date at ${after:0:7}"
        return
    fi

    # don't fly code that doesn't even compile: roll back to the previous version
    if ! python3 -m py_compile "$DIR"/*.py 2>/dev/null; then
        log "updated code ${after:0:7} does not compile, rolling back to ${before:0:7}"
        as_owner git -C "$top" reset --hard --quiet "$before"
        return
    fi
    log "updated ${before:0:7} -> ${after:0:7}"
}

ARGS=()
UPDATE=1
for a in "$@"; do
    if [ "$a" = "--no-update" ]; then UPDATE=0; else ARGS+=("$a"); fi
done
[ "$UPDATE" = 1 ] && update_from_github

for VENV in "$DIR/drone-env" "/home/maame/drone-env" "/home/maame/startup-files/drone-env"; do
    if [ -x "$VENV/bin/python3" ]; then PY="$VENV/bin/python3"; break; fi
done
if [ -z "$PY" ]; then
    log "drone-env venv not found, using system python3"
    PY=/usr/bin/python3
fi
cd "$DIR"
exec "$PY" "$DIR/maame_startup.py" "${ARGS[@]}"

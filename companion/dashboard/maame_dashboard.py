#!/usr/bin/env python3
"""
MaameDrone phone/tablet dashboard, served by the Pi on http://maame.local:8080
(or http://10.42.0.1:8080 on the Pi's hotspot). No internet needed.

Shows mode, armed, battery, GPS, height, distance home, mission step, the Pi
companion's state and recent messages; sends only Pause (BRAKE), RTL and Land.
Arming, launch and the motor kill stay on the laptop (ArduDeck).

Safety:
  * never sends HEARTBEAT and uses its own system id (254): a phone must not
    stand in for the laptop in the FC's GCS-lost failsafe (MAV_GCS_SYSID 255);
  * every request needs the PIN in /etc/maame/dashboard-pin (the hotspot is open);
    an optional view-only PIN (/etc/maame/dashboard-view-pin) can watch but not command;
  * commands are signed when /etc/maame/mavlink-signing.key exists.
Run as root (reads both root-only files): see maame-dashboard.service.
"""
import hmac
import json
import os
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from math import asin, cos, radians, sin, sqrt

HERE = os.path.dirname(os.path.abspath(__file__))
PIN_FILE = "/etc/maame/dashboard-pin"
# optional second PIN that can only watch (spectators): no commands
VIEW_PIN_FILE = "/etc/maame/dashboard-view-pin"
DASHBOARD_SYSID = 254
DASHBOARD_COMPID = 190
FC_SYSID = 1
PI_COMPID = 191
COPTER_MODES = {0: "STABILIZE", 2: "ALT_HOLD", 3: "AUTO", 4: "GUIDED", 5: "LOITER", 6: "RTL",
                9: "LAND", 16: "POSHOLD", 17: "BRAKE", 21: "SMART_RTL"}
ACTIONS = {"pause": 17, "rtl": 6, "land": 9}  # BRAKE holds position without sticks
MAV_STATE_ACTIVE = 4


def distance_m(lat1, lon1, lat2, lon2):
    h = sin(radians(lat2 - lat1) / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * asin(sqrt(h))


def new_state():
    return {"fc_seen": None, "mode": None, "armed": False, "volts": None, "battery_pct": None,
            "fix": 0, "sats": 0, "lat": None, "lon": None, "alt_m": None, "home": None,
            "home_dist_m": None, "mission_seq": None, "pi_seen": None, "pi_active": False,
            "messages": deque(maxlen=8)}


def apply_message(st, msg, now):
    """Fold one MAVLink message into the dashboard state (pure apart from st)."""
    t = msg.get_type()
    src = msg.get_srcComponent()
    if t == "HEARTBEAT" and msg.get_srcSystem() == FC_SYSID and src == 1:
        st["fc_seen"] = now
        st["mode"] = COPTER_MODES.get(msg.custom_mode, f"MODE {msg.custom_mode}")
        st["armed"] = bool(msg.base_mode & 128)
    elif t == "HEARTBEAT" and src == PI_COMPID:
        st["pi_seen"] = now
        st["pi_active"] = msg.system_status == MAV_STATE_ACTIVE
    elif t == "SYS_STATUS":
        st["volts"] = msg.voltage_battery / 1000 if msg.voltage_battery not in (0, 65535) else None
        st["battery_pct"] = msg.battery_remaining if msg.battery_remaining >= 0 else None
    elif t == "GPS_RAW_INT":
        st["fix"], st["sats"] = msg.fix_type, msg.satellites_visible
    elif t == "GLOBAL_POSITION_INT":
        st["lat"], st["lon"], st["alt_m"] = msg.lat / 1e7, msg.lon / 1e7, msg.relative_alt / 1000
    elif t == "HOME_POSITION":
        st["home"] = (msg.latitude / 1e7, msg.longitude / 1e7)
    elif t == "MISSION_CURRENT":
        st["mission_seq"] = msg.seq
    elif t == "STATUSTEXT":
        st["messages"].appendleft(msg.text)
    if st["home"] and st["lat"] is not None:
        st["home_dist_m"] = distance_m(st["home"][0], st["home"][1], st["lat"], st["lon"])


def snapshot(st, now):
    out = {k: v for k, v in st.items() if k not in ("messages", "fc_seen", "pi_seen", "home")}
    out["fc_online"] = st["fc_seen"] is not None and now - st["fc_seen"] < 3
    out["pi_online"] = st["pi_seen"] is not None and now - st["pi_seen"] < 3
    out["messages"] = list(st["messages"])
    return out


def pin_ok(sent, real):
    return bool(real) and hmac.compare_digest(str(sent or ""), real)


class Link:
    """MAVLink side: read the FC through mavlink-router, send mode changes."""

    def __init__(self, device="tcp:127.0.0.1:5760"):
        from pymavlink import mavutil
        sys.path.insert(0, os.path.join(HERE, "..", "startup-files"))
        self.mavutil = mavutil
        self.mav = mavutil.mavlink_connection(device, source_system=DASHBOARD_SYSID, source_component=DASHBOARD_COMPID)
        self.state = new_state()
        self.lock = threading.Lock()
        try:
            from maame_ready import load_signing_key, signed_timestamp
            self.key, self._signed_ts = load_signing_key(), signed_timestamp
        except Exception:
            self.key = None
        # Signing starts on the FC's first heartbeat (seeded from its timestamp, like the
        # companion): set up before that, pymavlink's signed commands were ignored by the FC.
        self.signing = False
        self._last_stream_req = 0.0

    def _start_signing(self, heartbeat):
        fc_ts = self._signed_ts(heartbeat.get_msgbuf())
        self.mav.setup_signing(self.key, sign_outgoing=True, link_id=3,
                               initial_timestamp=fc_ts + 1 if fc_ts else int((time.time() - 1420070400) * 1e5))
        self.signing = True
        print(f"MAVLink signing on (timestamp from {'FC' if fc_ts else 'Pi clock'})", flush=True)

    def run(self):
        while True:
            msg = self.mav.recv_match(blocking=True, timeout=1)
            now = time.monotonic()
            if msg is not None and msg.get_type() != "BAD_DATA":
                if (self.key and not self.signing and msg.get_type() == "HEARTBEAT"
                        and msg.get_srcSystem() == FC_SYSID and msg.get_srcComponent() == 1):
                    self._start_signing(msg)
                with self.lock:
                    apply_message(self.state, msg, now)
            # with no laptop asking, the FC streams little to this link: ask gently
            if now - self._last_stream_req > 10:
                self._last_stream_req = now
                self.mav.mav.request_data_stream_send(FC_SYSID, 1, self.mavutil.mavlink.MAV_DATA_STREAM_ALL, 2, 1)
                self.mav.mav.command_long_send(FC_SYSID, 1, self.mavutil.mavlink.MAV_CMD_REQUEST_MESSAGE, 0,
                                               242, 0, 0, 0, 0, 0, 0)  # HOME_POSITION

    def snapshot(self):
        with self.lock:
            return snapshot(self.state, time.monotonic())

    def send_action(self, action):
        """False while signing is not running yet: the FC would ignore the command."""
        if self.key and not self.signing:
            return False
        mode = ACTIONS[action]
        self.mav.mav.command_long_send(FC_SYSID, 1, self.mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0,
                                       self.mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode, 0, 0, 0, 0, 0)
        return True


def make_handler(link, pin, view_pin=None):
    page = open(os.path.join(HERE, "index.html"), "rb").read()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

        def log_message(self, *args):  # keep the journal quiet
            pass

        def do_GET(self):
            if self.path == "/" or self.path.startswith("/?"):
                return self._send(200, page, "text/html; charset=utf-8")
            if self.path == "/api/state":
                sent = self.headers.get("X-Maame-Pin")
                can_command = pin_ok(sent, pin)
                if not (can_command or pin_ok(sent, view_pin)):
                    return self._send(401, {"error": "PIN required"})
                return self._send(200, {**link.snapshot(), "can_command": can_command})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/cmd":
                return self._send(404, {"error": "not found"})
            if not pin_ok(self.headers.get("X-Maame-Pin"), pin):
                return self._send(401, {"error": "PIN required"})
            try:
                length = min(int(self.headers.get("Content-Length", 0)), 1024)
                action = json.loads(self.rfile.read(length) or b"{}").get("action")
            except (ValueError, AttributeError):
                action = None
            if action not in ACTIONS:
                return self._send(400, {"error": "action must be pause, rtl or land"})
            if link.send_action(action) is False:
                return self._send(503, {"error": "no signed link to the drone yet, try again in a moment"})
            print(f"dashboard: {action} from {self.client_address[0]}", flush=True)
            self._send(200, {"sent": action})

    return Handler


def main():
    try:
        pin = open(PIN_FILE).read().strip()
    except OSError:
        sys.exit(f"no PIN: create {PIN_FILE} (install-dashboard.sh does)")
    try:
        view_pin = open(VIEW_PIN_FILE).read().strip() or None
    except OSError:
        view_pin = None
    link = Link(sys.argv[1] if len(sys.argv) > 1 else "tcp:127.0.0.1:5760")
    threading.Thread(target=link.run, daemon=True).start()
    port = int(os.environ.get("MAAME_DASHBOARD_PORT", "8080"))
    print(f"Maame dashboard on :{port}", flush=True)
    ThreadingHTTPServer(("", port), make_handler(link, pin, view_pin)).serve_forever()


if __name__ == "__main__":
    main()

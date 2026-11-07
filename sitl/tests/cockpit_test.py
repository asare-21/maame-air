"""SITL: the Maame cockpit's GUIDED moves behave as the app expects (same fields as
apps/desktop/src/main/maame/cockpit.ts): offset nudge, held velocity, auto-stop when the
stick is released (no more targets), relative turn, climb nudge."""
import math, sys, threading, time
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "companion" / "startup-files"))
from maame_ready import CompanionLink
from pymavlink import mavutil
M = mavutil.mavlink
st = {"mode": None, "armed": False, "alt": 0.0, "lat": 0, "lon": 0, "hdg": 0.0, "vx": 0.0, "vy": 0.0, "ekf": 0}
res = []
def check(n, ok, d=""): res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)
gcs = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255, source_component=190)
stop = threading.Event()
threading.Thread(target=lambda: [(gcs.mav.heartbeat_send(6, 8, 0, 0, 0), time.sleep(1)) for _ in iter(int, 1) if not stop.is_set()], daemon=True).start()
gcs.wait_heartbeat(timeout=60); gcs.mav.request_data_stream_send(1, 1, M.MAV_DATA_STREAM_ALL, 10, 1)
pi = CompanionLink("tcp:127.0.0.1:5761")
threading.Thread(target=lambda: [(pi.tick(), time.sleep(0.05)) for _ in iter(int, 1) if not stop.is_set()], daemon=True).start()
def pump(sec, until=None):
    end = time.time() + sec
    while time.time() < end:
        m = gcs.recv_match(blocking=True, timeout=0.2)
        if m is None: continue
        t = m.get_type()
        if t == "HEARTBEAT" and m.get_srcComponent() == 1:
            st["mode"] = m.custom_mode; st["armed"] = bool(m.base_mode & 128)
        elif t == "GLOBAL_POSITION_INT":
            st.update(alt=m.relative_alt / 1000, lat=m.lat / 1e7, lon=m.lon / 1e7, hdg=m.hdg / 100, vx=m.vx / 100, vy=m.vy / 100)
        elif t == "EKF_STATUS_REPORT": st["ekf"] = m.flags
        if until and until(): return True
    return bool(until and until())
def dist(a, b):
    return math.hypot((b[0] - a[0]) * 111320, (b[1] - a[1]) * 111320 * math.cos(math.radians(a[0])))
def bearing(a, b):
    return math.degrees(math.atan2((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0])) % 360
def move(frame, mask, x=0, y=0, z=0, vx=0, vy=0, vz=0, yr=0):
    gcs.mav.set_position_target_local_ned_send(0, 1, 1, frame, mask, x, y, z, vx, vy, vz, 0, 0, 0, 0, yr)
MASK_VEL, MASK_OFF = 0b0101_1100_0111, 0b1101_1111_1000
check("EKF has a position", pump(150, lambda: st["ekf"] & 0x10 and st["lat"] != 0)); pump(3)
gcs.mav.command_long_send(1, 191, 31011, 0, 1, 0, 0, 0, 0, 0, 0); pump(2)       # Pi ready
gcs.mav.command_long_send(1, 1, 176, 0, 1, 4, 0, 0, 0, 0, 0); pump(2)            # GUIDED
gcs.mav.command_long_send(1, 1, 400, 0, 1, 0, 0, 0, 0, 0, 0)                     # arm
check("armed in GUIDED", pump(8, lambda: st["armed"] and st["mode"] == 4))
gcs.mav.command_long_send(1, 1, 22, 0, 0, 0, 0, 0, 0, 0, 5)                      # take off 5 m
check("took off to ~5 m", pump(25, lambda: st["alt"] > 4.6), f"alt {st['alt']:.1f}")
pump(4)
a = (st["lat"], st["lon"]); h0 = st["hdg"]
move(9, MASK_OFF, x=5); pump(10)
b = (st["lat"], st["lon"]); d = dist(a, b); brg = bearing(a, b)
err = abs((brg - h0 + 180) % 360 - 180)
check("nudge forward 5 m goes ~5 m along the heading", 4 < d < 6 and err < 20, f"{d:.1f} m, bearing {brg:.0f} vs heading {h0:.0f}")
a = (st["lat"], st["lon"]); t0 = time.time()
while time.time() - t0 < 3:
    move(9, MASK_VEL, vx=1); pump(0.1)
moved = dist(a, (st["lat"], st["lon"]))
check("held stick 1 m/s for 3 s moves ~3 m", 1.8 < moved < 4.5, f"{moved:.1f} m")
pump(5)  # no more targets: ArduCopter stops on its own
speed = math.hypot(st["vx"], st["vy"])
check("released stick: stops within ~5 s", speed < 0.3 and st["mode"] == 4, f"speed {speed:.2f} m/s")
h1 = st["hdg"]; gcs.mav.command_long_send(1, 1, 115, 0, 90, 45, 1, 1, 0, 0, 0); pump(6)
turned = (st["hdg"] - h1) % 360
check("turn +90 deg", 75 < turned < 105, f"{turned:.0f} deg")
alt0 = st["alt"]; move(9, MASK_OFF, z=-2); pump(8)
check("nudge up 2 m", 1.5 < st["alt"] - alt0 < 2.5, f"{st['alt'] - alt0:.1f} m")
gcs.mav.command_long_send(1, 1, 176, 0, 1, 9, 0, 0, 0, 0, 0)                     # LAND
check("lands and disarms", pump(40, lambda: not st["armed"]))
stop.set()
print("RESULT", "ALL PASS" if all(res) else "FAILURES")
import os as _os, sys as _sys; _sys.stdout.flush(); _os._exit(0)  # leave now: helper threads would keep the process alive (the runner reads RESULT)

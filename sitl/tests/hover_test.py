"""SITL test of the Maame hover test card: same mission + same start sequence the app sends."""
import sys, threading, time, math
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "companion" / "startup-files"))
from maame_ready import CompanionLink  # noqa: E402
from pymavlink import mavutil  # noqa: E402
M = mavutil.mavlink
H, HOLD = float(sys.argv[1]), int(sys.argv[2])
st = {"ekf": 0, "mode": None, "armed": False, "alt": 0.0, "lat": 0, "lon": 0, "seq": 0, "fix": 0}
stop = threading.Event(); res = []
def check(n, ok, d=""): res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)
gcs = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255, source_component=190)
def hb():
    while not stop.is_set(): gcs.mav.heartbeat_send(M.MAV_TYPE_GCS, M.MAV_AUTOPILOT_INVALID, 0, 0, 0); time.sleep(1)
threading.Thread(target=hb, daemon=True).start()
gcs.wait_heartbeat(timeout=60); gcs.mav.request_data_stream_send(1, 1, M.MAV_DATA_STREAM_ALL, 10, 1)
pi = CompanionLink("tcp:127.0.0.1:5761")
threading.Thread(target=lambda: [(pi.tick(), time.sleep(0.05)) for _ in iter(int, 1) if not stop.is_set()], daemon=True).start()
trace = []
def pump(sec, until=None):
    end = time.time() + sec
    while time.time() < end:
        m = gcs.recv_match(blocking=True, timeout=0.2)
        if m is None: continue
        t = m.get_type()
        if t == "HEARTBEAT" and m.get_srcComponent() == 1:
            st["mode"] = m.custom_mode; st["armed"] = bool(m.base_mode & M.MAV_MODE_FLAG_SAFETY_ARMED)
        elif t == "GLOBAL_POSITION_INT":
            st["alt"] = m.relative_alt / 1000; st["lat"] = m.lat / 1e7; st["lon"] = m.lon / 1e7
            trace.append((time.time(), st["alt"], st["armed"], st["lat"], st["lon"]))
        elif t == "GPS_RAW_INT": st["fix"] = m.fix_type
        elif t == "EKF_STATUS_REPORT": st["ekf"] = m.flags
        elif t == "STATUSTEXT" and any(k in m.text for k in ("Mission", "Land", "Disarm", "Arm", "Takeoff", "Pi", "PreArm")):
            print(f"      [{m.get_srcComponent()}] {m.text}", flush=True)
        if until and until(): return True
    return bool(until and until())
def set_mode(n):
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_DO_SET_MODE, 0, M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, n, 0, 0, 0, 0, 0)
    return pump(5, lambda: st["mode"] == n)
# wait for GPS + EKF so AUTO is allowed
ok = pump(300, lambda: st["fix"] >= 3 and st["ekf"] & 0x10 and st["lat"] != 0); pump(3)  # EKF_POS_HORIZ_ABS
check("EKF has a GPS position", bool(ok))
home = (st["lat"], st["lon"])
# Pi ready (button 2)
gcs.mav.command_long_send(1, 191, 31011, 0, 1, 0, 0, 0, 0, 0, 0); pump(3)
# upload: HOME, TAKEOFF h, LOITER_TIME hold @h, LAND  (hover-test.ts)
items = [(0, M.MAV_CMD_NAV_WAYPOINT, 0, 0), (3, M.MAV_CMD_NAV_TAKEOFF, 0, H), (3, M.MAV_CMD_NAV_LOITER_TIME, HOLD, H), (3, M.MAV_CMD_NAV_LAND, 0, 0)]
gcs.mav.mission_count_send(1, 1, len(items), 0); ack = None
while True:
    m = gcs.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT", "MISSION_ACK"], blocking=True, timeout=5)
    if m is None: break
    if m.get_type() == "MISSION_ACK": ack = m.type; break
    fr, cmd, p1, al = items[m.seq]
    gcs.mav.mission_item_int_send(1, 1, m.seq, {0: M.MAV_FRAME_GLOBAL, 3: M.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT}[fr], cmd, 0, 1, p1, 0, 0, 0, int(home[0] * 1e7), int(home[1] * 1e7), al, 0)
check("mission uploaded", ack == 0, f"ack={ack}")
# button: STABILIZE -> AUTO -> arm
check("STABILIZE", set_mode(0)); check("AUTO", set_mode(3))
gcs.mav.command_long_send(1, 1, M.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
check("armed", pump(8, lambda: st["armed"])); t_arm = time.time(); trace.clear()
pump(HOLD + 40, lambda: not st["armed"] and time.time() - t_arm > 3)
t_end = time.time(); stop.set()
air = [x for x in trace if x[1] > 0.15]
peak = max((x[1] for x in trace), default=0)
near = [x for x in trace if abs(x[1] - H) <= max(0.15, 0.2 * H)]
hover_s = (near[-1][0] - near[0][0]) if near else 0
drift = math.hypot((st["lat"] - home[0]) * 111320, (st["lon"] - home[1]) * 111320 * math.cos(math.radians(home[0])))
# ArduCopter mission takeoffs climb to at least ~1 m, then settle to a lower hover height
top = max(H, 1.0)
check("reached height", H - 0.2 <= peak <= top + max(0.25, 0.25 * top), f"peak {peak:.2f} m (target {H}, take-off at least 1 m)")
check("hovered", hover_s >= HOLD - 1, f"{hover_s:.1f} s near {H} m (asked {HOLD})")
check("landed and disarmed", not st["armed"] and st["alt"] < 0.2, f"alt {st['alt']:.2f} m, armed={st['armed']}")
check("landed on the spot", drift < 1.5, f"{drift:.2f} m from takeoff")
print(f"total arm->disarm {t_end - t_arm:.1f} s, airborne {len(air) / 10:.1f} s (approx)")
print("RESULT", "ALL PASS" if all(res) else "FAILURES")
import os as _os, sys as _sys; _sys.stdout.flush(); _os._exit(0)  # leave now: helper threads would keep the process alive (the runner reads RESULT)

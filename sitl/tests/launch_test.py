"""SITL end-to-end test of the Maame launch flow and emergency controls.
Drives the same MAVLink the ArduDeck UI sends (MaameFlightCard / MaameEmergencyBar);
the Pi is the real CompanionLink from companion/startup-files/maame_ready.py.
"""
import sys, threading, time
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "companion" / "startup-files"))
from maame_ready import CompanionLink  # noqa: E402
from pymavlink import mavutil  # noqa: E402

M = mavutil.mavlink
MODES = {3: "AUTO", 4: "GUIDED", 6: "RTL", 9: "LAND", 17: "BRAKE", 0: "STABILIZE", 5: "LOITER"}
state = {"mode": None, "armed": False, "alt": 0.0, "vx": 0, "vy": 0, "seq": 0, "texts": [], "pi_status": None}
gcs_hb = threading.Event(); gcs_hb.set()
stop = threading.Event()
results = []

def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)

gcs = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255, source_component=190)
def gcs_heartbeat():
    while not stop.is_set():
        if gcs_hb.is_set():
            gcs.mav.heartbeat_send(M.MAV_TYPE_GCS, M.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        time.sleep(1)
threading.Thread(target=gcs_heartbeat, daemon=True).start()
gcs.wait_heartbeat(timeout=60)
gcs.mav.request_data_stream_send(1, 1, M.MAV_DATA_STREAM_ALL, 5, 1)

pi = CompanionLink("tcp:127.0.0.1:5761")
def pi_loop():
    while not stop.is_set():
        pi.tick(); time.sleep(0.05)
threading.Thread(target=pi_loop, daemon=True).start()

def pump(sec, until=None):
    end = time.time() + sec
    while time.time() < end:
        m = gcs.recv_match(blocking=True, timeout=0.2)
        if m is None: continue
        t = m.get_type()
        if t == "HEARTBEAT" and m.get_srcComponent() == 1:
            state["mode"] = m.custom_mode; state["armed"] = bool(m.base_mode & M.MAV_MODE_FLAG_SAFETY_ARMED)
        elif t == "HEARTBEAT" and m.get_srcComponent() == 191:
            state["pi_status"] = m.system_status
        elif t == "GLOBAL_POSITION_INT":
            state["alt"] = m.relative_alt / 1000; state["vx"] = m.vx; state["vy"] = m.vy
        elif t == "MISSION_CURRENT":
            state["seq"] = m.seq
        elif t == "STATUSTEXT":
            state["texts"].append(m.text); print(f"      [{m.get_srcComponent()}] {m.text}", flush=True)
        if until and until(): return True
    return bool(until and until())

def set_mode(n):
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_DO_SET_MODE, 0, M.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, n, 0, 0, 0, 0, 0)
    return pump(5, lambda: state["mode"] == n)

def arm(on, force=False):
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1 if on else 0, 21196 if force else 0, 0, 0, 0, 0, 0)
    return pump(5, lambda: state["armed"] == on)

def prearm_blockers():
    state["texts"].clear()
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_RUN_PREARM_CHECKS, 0, 0, 0, 0, 0, 0, 0, 0)
    pump(3)
    return [t for t in state["texts"] if t.startswith("PreArm")]

# --- 0. wait for GPS / EKF (only the Pi gate may block)
t0 = time.time()
while time.time() - t0 < 300:  # a wiped SITL needs a while for GPS + home
    b = prearm_blockers()
    if all("Pi companion not ready" in x for x in b): break
    time.sleep(3)
check("0. sim ready, only the Pi gate blocks arming", all("Pi companion not ready" in x for x in b), str(b))

# --- 1. gate: arming refused while the Pi is on standby
set_mode(3); state["texts"].clear()
check("1. arm refused while Pi on STANDBY", not arm(True) and any("Pi companion not ready" in t for t in state["texts"]))

# --- 2. mission upload (takeoff 10 m, two waypoints ~33 m out, RTL)
lat0, lon0 = -35.363261, 149.165230
items = [(lat0, lon0, 0, M.MAV_CMD_NAV_WAYPOINT), (lat0, lon0, 10, M.MAV_CMD_NAV_TAKEOFF),
         (lat0 + 0.0003, lon0, 10, M.MAV_CMD_NAV_WAYPOINT), (lat0 + 0.0003, lon0 + 0.0004, 10, M.MAV_CMD_NAV_WAYPOINT),
         (0, 0, 0, M.MAV_CMD_NAV_RETURN_TO_LAUNCH)]
gcs.mav.mission_count_send(1, 1, len(items), 0)
ack = None; t0 = time.time()
while time.time() - t0 < 15 and ack is None:
    m = gcs.recv_match(type=["MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"], blocking=True, timeout=1)
    if m is None: continue
    if m.get_type() == "MISSION_ACK": ack = m.type; break
    la, lo, al, cmd = items[m.seq]
    gcs.mav.mission_item_int_send(1, 1, m.seq, M.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, cmd, 0, 1, 0, 0, 0, 0, int(la * 1e7), int(lo * 1e7), al, 0)
check("2. mission uploaded", ack == 0, f"ack={ack}")

# --- 3. Pi ready (MaameFlightCard step 2: MAV_CMD_USER_2 to comp 191)
state["texts"].clear()
gcs.mav.command_long_send(1, 191, 31011, 0, 1, 0, 0, 0, 0, 0, 0)
check("3. Pi goes ACTIVE, gate opens", pump(6, lambda: state["pi_status"] == 4 and any("Pi companion ready" in t for t in state["texts"])))

# --- 4. launch (step 3, same order as MaameFlightCard: STABILIZE -> AUTO -> arm, no throttle)
set_mode(0)
set_mode(3)
check("4a. armed in AUTO", arm(True))
check("4b. took off to ~10 m on its own", pump(30, lambda: state["alt"] > 8.5), f"alt={state['alt']:.1f} m")
pump(30, lambda: state["seq"] >= 3)
check("4c. flying the mission", state["seq"] >= 2, f"mission item {state['seq']}")

# --- 5. Pause = BRAKE holds position
set_mode(17); pump(4)
speed = (state["vx"] ** 2 + state["vy"] ** 2) ** 0.5 / 100
check("5. Pause (BRAKE) stops and holds", state["mode"] == 17 and speed < 0.5 and state["armed"], f"speed {speed:.2f} m/s, alt {state['alt']:.1f} m")

# --- 6. Resume AUTO
check("6. Resume (AUTO)", set_mode(3))

# --- 7. lost ground link in AUTO: mission continues (FS_GCS_ENABLE 1 + FS_OPTIONS 10)
gcs_hb.clear(); pump(9); gcs_hb.set()
check("7. GCS link lost 9 s in AUTO: kept flying the mission", state["mode"] == 3 and state["armed"], f"mode {MODES.get(state['mode'])}")

# --- 8. RTL
check("8. RTL", set_mode(6))
pump(6)

# --- 9. Land
check("9. Land", set_mode(9))
pump(4)
alt_before = state["alt"]

# --- 10. motor kill (hold-to-kill = force disarm) while still airborne
airborne = alt_before > 1.5
killed = arm(False, force=True)
check("10. motor kill disarms in the air", killed and airborne, f"alt at kill {alt_before:.1f} m")

# --- 11. Pi back to standby
gcs.mav.command_long_send(1, 191, 31011, 0, 0, 0, 0, 0, 0, 0, 0)
check("11. Pi back to STANDBY", pump(5, lambda: state["pi_status"] == 3))

stop.set()
print(f"\n{sum(ok for _, ok in results)}/{len(results)} passed")
print("RESULT", "ALL PASS" if all(ok for _, ok in results) else "FAILURES")
import os as _os, sys as _sys; _sys.stdout.flush(); _os._exit(0)  # leave now: helper threads would keep the process alive (the runner reads RESULT)

"""SITL test of the Maame props-off motor vibration card: with GPS switched off, each
MAV_CMD_DO_MOTOR_TEST is accepted and spins exactly one motor, and VIBRATION keeps
streaming (same commands the app sends: 15 %, 3 s, one motor at a time)."""
import sys, threading, time
from pymavlink import mavutil
M = mavutil.mavlink
res = []
def check(n, ok, d=""): res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)
gcs = mavutil.mavlink_connection("tcp:127.0.0.1:5760", source_system=255, source_component=190)
stop = threading.Event()
def hb():
    while not stop.is_set(): gcs.mav.heartbeat_send(M.MAV_TYPE_GCS, M.MAV_AUTOPILOT_INVALID, 0, 0, 0); time.sleep(1)
threading.Thread(target=hb, daemon=True).start()
gcs.wait_heartbeat(timeout=60); gcs.mav.request_data_stream_send(1, 1, M.MAV_DATA_STREAM_ALL, 10, 1)
st = {"fix": None, "servo": [0] * 4, "vibe": None, "vibe_n": 0, "ack": {}, "armed": False}
def pump(sec, until=None):
    end = time.time() + sec
    while time.time() < end:
        m = gcs.recv_match(blocking=True, timeout=0.2)
        if m is None: continue
        t = m.get_type()
        if t == "GPS_RAW_INT": st["fix"] = m.fix_type
        elif t == "SERVO_OUTPUT_RAW": st["servo"] = [m.servo1_raw, m.servo2_raw, m.servo3_raw, m.servo4_raw]
        elif t == "VIBRATION": st["vibe"] = max(m.vibration_x, m.vibration_y, m.vibration_z); st["vibe_n"] += 1
        elif t == "COMMAND_ACK": st["ack"][m.command] = m.result
        elif t == "HEARTBEAT" and m.get_srcComponent() == 1: st["armed"] = bool(m.base_mode & M.MAV_MODE_FLAG_SAFETY_ARMED)
        elif t == "STATUSTEXT": print(f"      [{m.get_srcComponent()}] {m.text}", flush=True)
        if until and until(): return True
    return bool(until and until())

# GPS off: SIM_GPS1_ENABLE on 4.6+, SIM_GPS_DISABLE before that (whichever exists takes it)
for name, val in (("SIM_GPS1_ENABLE", 0), ("SIM_GPS_DISABLE", 1)):
    gcs.mav.param_set_send(1, 1, name.encode(), val, M.MAV_PARAM_TYPE_REAL32)
pump(8)
st["fix"] = None; pump(4)
check("no GPS fix", (st["fix"] or 0) < 3, f"fix_type={st['fix']}")
idle = st["servo"][:]
spun = []
for seq in range(1, 5):
    st["ack"].pop(M.MAV_CMD_DO_MOTOR_TEST, None); n0 = st["vibe_n"]
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_DO_MOTOR_TEST, 0, seq, M.MOTOR_TEST_THROTTLE_PERCENT, 15, 3, 0, 0, 0)
    pump(2, lambda: M.MAV_CMD_DO_MOTOR_TEST in st["ack"])
    ack = st["ack"].get(M.MAV_CMD_DO_MOTOR_TEST)
    check(f"motor test {seq} accepted", ack == M.MAV_RESULT_ACCEPTED, f"ack={ack}")
    pump(1.5)
    high = [i for i, (now, was) in enumerate(zip(st["servo"], idle)) if now > was + 50]
    check(f"motor test {seq} spins one motor", len(high) == 1, f"servo {st['servo']} (idle {idle})")
    # the app's card relies on this: armed while a motor test spins, disarmed again within 4 s
    check(f"FC reports armed while motor {seq} spins", st["armed"])
    spun += high
    t_end = time.time() + 1.5
    pump(5.5, lambda: time.time() > t_end and not st["armed"])
    check(f"FC disarmed within 4 s after motor {seq}", not st["armed"], f"{time.time() - t_end:.1f} s after the test ended")
    check(f"vibration streams during motor {seq}", st["vibe_n"] > n0, f"{st['vibe_n'] - n0} msgs, last {st['vibe'] or 0:.2f} m/s²")
check("every motor spun once", sorted(spun) == [0, 1, 2, 3], f"outputs {spun}")
pump(2)
check("all stopped and disarmed after", not st["armed"] and all(s <= i + 50 for s, i in zip(st["servo"], idle)), f"servo {st['servo']}")
stop.set()
print("RESULT ALL PASS" if all(res) else "RESULT FAIL", flush=True)

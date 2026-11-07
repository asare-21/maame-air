"""SITL: Maame with MAVLink2 signing on - FC + real gate + real CompanionLink."""
import os, sys, threading, time
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "companion" / "startup-files"))
import maame_ready
from pymavlink import mavutil
M = mavutil.mavlink
KEY = os.urandom(32); WRONG = os.urandom(32)
res = []
def check(n, ok, d=""): res.append(ok); print(f"{'PASS' if ok else 'FAIL'}  {n}  {d}", flush=True)
def ts(): return int((time.time() - 1420070400) * 1e5)

gcs = mavutil.mavlink_connection("tcp:127.0.0.1:5762", source_system=255, source_component=190)
gcs.wait_heartbeat(timeout=60)
# 1. give the FC the key (unsigned SETUP_SIGNING, as ArduDeck "Send to FC" does), then sign ourselves
for _ in range(2): gcs.mav.setup_signing_send(1, 1, list(KEY), ts())
time.sleep(1)
gcs.setup_signing(KEY, sign_outgoing=True, initial_timestamp=ts(), link_id=2)
def hb_loop(conn, stop):
    while not stop.is_set(): conn.mav.heartbeat_send(6, 8, 0, 0, 0); time.sleep(1)
stop = threading.Event(); threading.Thread(target=hb_loop, args=(gcs, stop), daemon=True).start()

def fc_signed(conn, sec=5):
    end = time.time() + sec
    while time.time() < end:
        m = conn.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if m and m.get_srcComponent() == 1:
            b = m.get_msgbuf(); return bool(b[0] == 0xFD and b[2] & 1)
    return None
check("FC signs after SETUP_SIGNING", fc_signed(gcs) is True)

def mode_change(conn, mode, sec=4):
    conn.mav.command_long_send(1, 1, M.MAV_CMD_DO_SET_MODE, 0, 1, mode, 0, 0, 0, 0, 0)
    end = time.time() + sec
    while time.time() < end:
        m = conn.recv_match(type=["HEARTBEAT", "COMMAND_ACK"], blocking=True, timeout=0.5)
        if m and m.get_type() == "COMMAND_ACK" and m.command == M.MAV_CMD_DO_SET_MODE: return m.result
    return None

# 2. unsigned client on another port is ignored
rogue = mavutil.mavlink_connection("tcp:127.0.0.1:5764", source_system=254, source_component=190)
rogue.wait_heartbeat(timeout=10)
check("unsigned client's command ignored", mode_change(rogue, 5) is None)
check("signed GCS command accepted", mode_change(gcs, 5) == 0)
mode_change(gcs, 0)

def pi_run(key, sec):
    maame_ready.load_signing_key = lambda *a, **k: key
    pi = maame_ready.CompanionLink("tcp:127.0.0.1:5761")
    end = time.time() + sec
    while time.time() < end: pi.tick(); time.sleep(0.05)
    return pi
def prearm_texts():
    gcs.mav.command_long_send(1, 1, M.MAV_CMD_RUN_PREARM_CHECKS, 0, 0, 0, 0, 0, 0, 0, 0)
    out = set(); end = time.time() + 4
    while time.time() < end:
        m = gcs.recv_match(type="STATUSTEXT", blocking=True, timeout=0.5)
        if m and m.text.startswith("PreArm"): out.add(m.text)
    return out

# 3. Pi with the right key: its signed ACTIVE heartbeat opens the gate
holder = {}
def pi_thread(key, sec): holder["pi"] = pi_run(key, sec)
t = threading.Thread(target=pi_thread, args=(KEY, 25)); t.start(); time.sleep(3)
gcs.mav.command_long_send(1, 191, 31011, 0, 1, 0, 0, 0, 0, 0, 0); time.sleep(3)
pa = prearm_texts()
check("Pi (right key) opens the gate", not any("Pi companion" in x for x in pa), str(sorted(pa))[:120])
t.join()
time.sleep(4)  # gate times out after 3 s
# 4. Pi with a wrong key: FC drops its heartbeats, gate stays closed
t = threading.Thread(target=pi_thread, args=(WRONG, 20)); t.start(); time.sleep(3)
gcs.mav.command_long_send(1, 191, 31011, 0, 1, 0, 0, 0, 0, 0, 0); time.sleep(3)
pa = prearm_texts()
check("Pi (wrong key) cannot open the gate", any("Pi companion" in x for x in pa), str(sorted(pa))[:120])
t.join(); stop.set()
print("RESULT", "ALL PASS" if all(res) else "FAILURES")
import os as _os, sys as _sys; _sys.stdout.flush(); _os._exit(0)  # leave now: helper threads would keep the process alive (the runner reads RESULT)

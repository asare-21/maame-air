import sys, threading, time
REPO = __import__("pathlib").Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "companion" / "dashboard"))
import maame_dashboard as d
from pymavlink import mavutil
watch = mavutil.mavlink_connection("tcp:127.0.0.1:5762", source_system=250)  # sees what the FC routes
watch.wait_heartbeat(timeout=60)
link = d.Link("tcp:127.0.0.1:5761")
threading.Thread(target=link.run, daemon=True).start()
end = time.time() + 60
while time.time() < end:
    s = link.snapshot()
    if s["fc_online"] and s["fix"] >= 3 and s["alt_m"] is not None: break
    time.sleep(1)
print("state:", {k: s[k] for k in ("fc_online", "mode", "armed", "fix", "sats", "volts", "alt_m")})
link.send_action("land"); time.sleep(3)
print("after Land:", link.snapshot()["mode"])
hb254 = 0; end = time.time() + 5
while time.time() < end:
    m = watch.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
    if m and m.get_srcSystem() == 254: hb254 += 1
print("heartbeats from the dashboard (sysid 254):", hb254)
ok = s["fc_online"] and s["fix"] >= 3 and link.snapshot()["mode"] == "LAND" and hb254 == 0
print("RESULT", "ALL PASS" if ok else "FAIL")
import os as _os, sys as _sys; _sys.stdout.flush(); _os._exit(0)  # leave now: helper threads would keep the process alive (the runner reads RESULT)

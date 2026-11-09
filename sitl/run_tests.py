#!/usr/bin/env python3
"""
Maame simulator tests: real ArduCopter SITL + the Maame parameters + this repo's
arming gate (ardupilot/scripts) + the real Pi companion / dashboard code.

    python3 sitl/run_tests.py              # all tests
    python3 sitl/run_tests.py hover signing

Runs the tests with PYTHON if set; otherwise with sitl/.venv, created and filled from
companion/startup-files/requirements.txt on first use. Needs an ArduCopter SITL binary
(ARDUCOPTER, default: the one ArduDeck downloads).
Each test gets a fresh SITL in its own temporary folder; a test passes when it prints
"RESULT ALL PASS" within its time limit.
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERE = REPO / "sitl"
DEFAULT_BINARY = os.path.expanduser(
    "~/Library/Application Support/@ardudeck/desktop/ardupilot-sitl/macos/*/copter/arducopter")

# name: (script, args, uses SITL serial0 itself, time limit s)
TESTS = {
    "launch": ("launch_test.py", [], True, 720),
    "hover": ("hover_test.py", ["1", "8"], True, 480),
    "hover-low": ("hover_test.py", ["0.5", "5"], True, 480),
    "signing": ("signing_test.py", [], False, 300),
    "dashboard": ("dashboard_test.py", [], False, 240),
    "cockpit": ("cockpit_test.py", [], True, 540),
    "motor-vibe": ("motor_vibe_test.py", [], True, 180),
}


def find_binary():
    path = os.environ.get("ARDUCOPTER") or next(iter(sorted(glob.glob(DEFAULT_BINARY), reverse=True)), None)
    if not path or not os.access(path, os.X_OK):
        sys.exit("no ArduCopter SITL binary: set ARDUCOPTER=/path/to/arducopter (or let ArduDeck download one)")
    return path


def test_python():
    """PYTHON if set, else sitl/.venv with the companion's requirements (installed when missing)."""
    if os.environ.get("PYTHON"):
        return os.environ["PYTHON"]
    venv = HERE / ".venv"
    py = venv / "bin" / "python"
    if not py.exists():
        print(f"creating {venv}", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    if subprocess.run([str(py), "-c", "import pymavlink"], capture_output=True).returncode:
        print("installing the test requirements into sitl/.venv", flush=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", "-r",
                        str(REPO / "companion" / "startup-files" / "requirements.txt")], check=True)
    return str(py)


def run(name, binary, python):
    script, args, uses_serial0, limit = TESTS[name]
    work = Path(tempfile.mkdtemp(prefix=f"maame-sitl-{name}-"))
    shutil.copytree(REPO / "ardupilot" / "scripts", work / "scripts")
    for p in (HERE / "params").glob("*.parm"):
        shutil.copy(p, work)
    sitl_log = open(work / "sitl.log", "w")
    # SERIAL3 is the simulated GPS in SITL: never take it over (the extra port is SERIAL4, TCP 5764)
    sitl = subprocess.Popen([binary, "-M", "quad", "-w", "--defaults", "copter.parm,maame.parm",
                             "--serial0", "tcp:0", "--serial1", "tcp:1", "--serial2", "tcp:2", "--serial4", "tcp:4"],
                            cwd=work, stdout=sitl_log, stderr=subprocess.STDOUT)
    holder = None
    ok = False
    try:
        time.sleep(3)
        if not uses_serial0:  # SITL waits for a client on serial0 before it runs
            holder = subprocess.Popen([python, "-c", (
                "from pymavlink import mavutil\n"
                "m = mavutil.mavlink_connection('tcp:127.0.0.1:5760')\n"
                "while True: m.recv_match(blocking=True, timeout=1)")],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
        t0 = time.time()
        try:
            r = subprocess.run([python, str(HERE / "tests" / script), *args], cwd=work,
                               capture_output=True, text=True, timeout=limit)
            out = r.stdout + r.stderr
        except subprocess.TimeoutExpired as e:
            out = "".join(x.decode() if isinstance(x, bytes) else (x or "") for x in (e.stdout, e.stderr))
            out += f"\nTIMEOUT after {limit} s"
        (work / "test.log").write_text(out)  # kept with sitl.log when the test fails
        ok = "RESULT ALL PASS" in out
        keep = ("PASS", "FAIL", "RESULT", "TIMEOUT", "state:", "after", "heartbeats", "total")
        print(f"\n== {name}: {'PASS' if ok else 'FAIL'} ({time.time() - t0:.0f} s)", flush=True)
        for line in out.splitlines():
            if line.startswith(keep):
                print("   " + line)
        if not ok:
            print(f"   logs kept in {work} (test.log, sitl.log)")
            print("   last lines: " + " | ".join(out.strip().splitlines()[-4:]))
        return ok
    finally:
        for p in (holder, sitl):
            if p:
                p.kill()
                p.wait()
        sitl_log.close()
        if ok:
            shutil.rmtree(work, ignore_errors=True)


def main():
    names = sys.argv[1:] or list(TESTS)
    unknown = [n for n in names if n not in TESTS]
    if unknown:
        sys.exit(f"unknown test(s) {unknown}; choose from {list(TESTS)}")
    binary, python = find_binary(), test_python()
    results = {n: run(n, binary, python) for n in names}
    print("\n" + ", ".join(f"{n} {'PASS' if ok else 'FAIL'}" for n, ok in results.items()))
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()

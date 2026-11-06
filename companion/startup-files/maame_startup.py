#!/usr/bin/env python3
"""MaameDrone startup: check everything is in place, test all LEDs, then start.

Order:
  1. Pre-flight checks (files, Python modules, UART config, /dev/serial0 free).
  2. LED self-test: PI, DATA, B-H, B-M, B-L one at a time, then all together.
  3. Start the live LED / companion loop (maame_battery_leds.run_live).

If a check fails, the red B-L LED flashes fast (5 Hz) for 10 s, the reason is
printed (see it with: journalctl -u maame-startup -e), and the script exits 1
so systemd retries after a few seconds.

    python3 maame_startup.py              # checks + LED test + live
    python3 maame_startup.py --check-only # checks + LED test, then exit
    python3 maame_startup.py --skip-led-test
"""
import argparse
import importlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REQUIRED_FILES = ("maame_leds.py", "maame_ready.py", "maame_battery_leds.py")
REQUIRED_MODULES = ("gpiozero", "lgpio", "pymavlink")
CONFIG_TXT = ("/boot/firmware/config.txt", "/boot/config.txt")
CMDLINE_TXT = ("/boot/firmware/cmdline.txt", "/boot/cmdline.txt")
SERIAL_DEV = "/dev/serial0"

failures = []


def ok(msg):
    print(f"  [ OK ] {msg}", flush=True)


def fail(msg):
    print(f"  [FAIL] {msg}", flush=True)
    failures.append(msg)


def warn(msg):
    print(f"  [WARN] {msg}", flush=True)


def first_existing(paths):
    return next((p for p in paths if os.path.exists(p)), None)


def check_files():
    for name in REQUIRED_FILES:
        if os.path.isfile(os.path.join(HERE, name)):
            ok(f"{name} present")
        else:
            fail(f"{name} missing from {HERE}")


def check_modules():
    print(f"  python: {sys.executable}")
    for mod in REQUIRED_MODULES:
        try:
            importlib.import_module(mod)
            ok(f"module {mod}")
        except Exception as exc:  # ImportError or a broken install
            fail(f"module {mod} not importable ({exc}); pip install {mod} in this venv")


def check_uart_config():
    cfg = first_existing(CONFIG_TXT)
    if cfg is None:
        warn("config.txt not found, skipping UART config check")
    else:
        lines = [l.split("#")[0].strip() for l in open(cfg)]
        if "enable_uart=1" in lines:
            ok(f"enable_uart=1 in {cfg}")
        else:
            fail(f"enable_uart=1 missing from {cfg}")
        if any(l.startswith("dtoverlay=disable-bt") for l in lines):
            ok(f"dtoverlay=disable-bt in {cfg}")
        else:
            fail(f"dtoverlay=disable-bt missing from {cfg} (serial0 would be the weak mini-UART)")

    cmd = first_existing(CMDLINE_TXT)
    if cmd:
        text = open(cmd).read()
        if "console=serial0" in text or "console=ttyAMA0" in text or "console=ttyS0" in text:
            fail(f"serial login console still enabled in {cmd}; raspi-config > Interface > Serial: login shell No")
        else:
            ok("no login console on the serial port")


def check_serial():
    if not os.path.exists(SERIAL_DEV):
        fail(f"{SERIAL_DEV} does not exist (UART not enabled, reboot after config change)")
        return
    target = os.path.realpath(SERIAL_DEV)
    ok(f"{SERIAL_DEV} -> {target}")
    if target.endswith("ttyS0"):
        warn("serial0 is the mini-UART (ttyS0); 921600 baud is unreliable there")
    try:
        out = subprocess.run(["fuser", target], capture_output=True, text=True, timeout=5)
        pids = [p for p in out.stdout.split() if p.isdigit() and int(p) != os.getpid()]
        if pids:
            fail(f"{target} already in use by PID {' '.join(pids)} (only one program can open it; "
                 "stop maame-battery-leds.service or the mission script)")
        else:
            ok(f"{target} is free")
    except FileNotFoundError:
        warn("fuser not installed, cannot check whether the port is free")
    except subprocess.TimeoutExpired:
        warn("fuser timed out")


def led_self_test():
    from gpiozero import LED
    from maame_leds import PIN_PI, PIN_DATA, PIN_BH, PIN_BM, PIN_BL
    names = (("PI", PIN_PI), ("DATA", PIN_DATA), ("B-H", PIN_BH), ("B-M", PIN_BM), ("B-L", PIN_BL))
    leds = [(name, pin, LED(pin)) for name, pin in names]
    try:
        for name, pin, led in leds:
            print(f"  LED {name} (GPIO{pin}) on", flush=True)
            led.on(); time.sleep(0.6); led.off(); time.sleep(0.15)
        print("  all LEDs on", flush=True)
        for _, _, led in leds:
            led.on()
        time.sleep(1.0)
    finally:
        for _, _, led in leds:
            led.off()
            led.close()
    ok("LED self-test done (watch the board: each LED once, then all five)")


def signal_failure(seconds=10):
    """Fast red flash so a failed start is visible without a screen."""
    try:
        from gpiozero import LED
        from maame_leds import PIN_BL
        red = LED(PIN_BL)
        red.blink(on_time=0.1, off_time=0.1, n=int(seconds * 5), background=False)
        red.close()
    except Exception as exc:
        print(f"  (could not flash B-L: {exc})")


def main():
    ap = argparse.ArgumentParser(description="MaameDrone startup checks + LED test")
    ap.add_argument("--check-only", action="store_true", help="exit after checks and LED test")
    ap.add_argument("--skip-led-test", action="store_true")
    ap.add_argument("--device", default=SERIAL_DEV)
    ap.add_argument("--baud", type=int, default=921600)
    args = ap.parse_args()

    print("== MaameDrone startup checks ==", flush=True)
    check_files()
    check_modules()
    check_uart_config()
    check_serial()

    if failures:
        print(f"\n{len(failures)} check(s) failed, not starting:", flush=True)
        for f in failures:
            print(f"  - {f}")
        signal_failure()
        sys.exit(1)

    if not args.skip_led_test:
        print("== LED self-test ==", flush=True)
        led_self_test()

    if args.check_only:
        print("All checks passed.")
        return

    print("== Starting live LEDs / companion link ==", flush=True)
    from maame_battery_leds import run_live
    run_live(args.device, args.baud)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Battery LEDs on the MaameDrone V1.0 board, as a standalone script.

    B-H  D5 green   GPIO19  battery >= 50 %
    B-M  D6 yellow  GPIO21  battery 25-50 %
    B-L  D7 red     GPIO18  battery < 25 %, flashing at the FC's low-battery failsafe

It reads the battery from the flight controller over /dev/serial0 and asks the
FC to stream SYS_STATUS and BATTERY_STATUS once a second, so no SRx_ parameter
change is needed. It also runs the PI and DATA LEDs.

Run it on its own for bench tests:
    python3 maame_battery_leds.py              # live, from the FC
    python3 maame_battery_leds.py --test       # cycle all five LEDs, no FC needed

Only one program can open /dev/serial0. Once the mission script runs, use
CompanionLink(leds=StatusLeds()) inside it instead of this script.
"""
import argparse
import time

from maame_leds import StatusLeds, PIN_PI, PIN_DATA, PIN_BH, PIN_BM, PIN_BL

MSG_SYS_STATUS = 1
MSG_BATTERY_STATUS = 147
STREAM_RATE_HZ = 1
LOOP_S = 0.05


def request_battery_stream(link):
    from pymavlink import mavutil
    for msg_id in (MSG_SYS_STATUS, MSG_BATTERY_STATUS):
        link.mav.mav.command_long_send(
            1, mavutil.mavlink.MAV_COMP_ID_AUTOPILOT1,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
            msg_id, 1_000_000 / STREAM_RATE_HZ, 0, 0, 0, 0, 0)


def run_live(device, baud):
    from maame_ready import CompanionLink
    leds = StatusLeds()
    link = CompanionLink(device, baud, leds=leds)
    print(f"Waiting for the flight controller on {device} ...")
    link.wait_for_fc()
    request_battery_stream(link)
    print("Connected. Battery LEDs are live (Ctrl+C to stop).")
    last_print, last_request = 0.0, time.monotonic()
    try:
        while True:
            link.tick()
            now = time.monotonic()
            if leds.level is None and now - last_request > 5:
                request_battery_stream(link)  # FC rebooted or ignored the first request
                last_request = now
            if now - last_print > 5:
                volts = f"{leds._volt_mv / 1000:.2f} V" if leds._volt_mv else "no voltage yet"
                print(f"battery: {leds.level or 'unknown'}, {volts}, failsafe={leds.failsafe}")
                last_print = now
            time.sleep(LOOP_S)
    finally:
        leds.off()


def run_test():
    from gpiozero import LED
    leds = {name: LED(pin) for name, pin in (("PI", PIN_PI), ("DATA", PIN_DATA),
                                                ("B-H", PIN_BH), ("B-M", PIN_BM), ("B-L", PIN_BL))}
    try:
        for name, led in leds.items():
            print(f"{name} on")
            led.on(); time.sleep(1.5); led.off()
        print("B-L flashing (failsafe pattern)")
        leds["B-L"].blink(on_time=0.5, off_time=0.5, n=4, background=False)
        print("Done. Each LED should have lit once, then red flashed 4 times.")
    finally:
        for led in leds.values():
            led.off()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--test", action="store_true", help="cycle all five LEDs without the FC")
    ap.add_argument("--device", default="/dev/serial0")
    ap.add_argument("--baud", type=int, default=921600)
    args = ap.parse_args()
    run_test() if args.test else run_live(args.device, args.baud)

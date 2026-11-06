#!/usr/bin/env python3
"""Companion-side half of the Maame arming gate.

Sends the HEARTBEAT that maame_pi_gate.lua on the flight controller watches:
component 191 (onboard computer), system_status STANDBY until the mission
service says it is ready, then ACTIVE. Call tick() from the main loop at least
once a second. If the main loop hangs or crashes, heartbeats stop and the FC
blocks arming (or reacts in flight) within 3 seconds.

It also reports whether the pilot has taken over, so the mission code can stop
sending commands when the FC is in any mode other than GUIDED or AUTO.

Pass leds=StatusLeds() (maame_leds.py) to drive the carrier board's status LEDs.

Usage:
    link = CompanionLink("/dev/serial0", 921600)
    link.wait_for_fc()
    ... run self-checks ...
    link.set_ready(True)
    while True:
        link.tick()
        if link.pilot_has_control():
            continue  # do not send commands
        ...
"""
import time

from pymavlink import mavutil

COPTER_MODE_AUTO = 3
COPTER_MODE_GUIDED = 4
COMPANION_MODES = (COPTER_MODE_AUTO, COPTER_MODE_GUIDED)
HEARTBEAT_PERIOD_S = 0.5
# MAVLink2 signing key shared with the FC and ArduDeck: 64 hex chars, root-only.
SIGNING_KEY_FILE = "/etc/maame/mavlink-signing.key"
SIGNING_LINK_ID = 1


def load_signing_key(path=SIGNING_KEY_FILE):
    """32-byte key from the key file, or None when signing is not set up."""
    try:
        key = bytes.fromhex(open(path).read().strip())
    except (OSError, ValueError):
        return None
    return key if len(key) == 32 else None


def signed_timestamp(msgbuf):
    """48-bit signing timestamp of a signed MAVLink2 frame, or None if unsigned."""
    if len(msgbuf) < 25 or msgbuf[0] != 0xFD or not msgbuf[2] & 0x01:
        return None
    return int.from_bytes(msgbuf[-12:-6], "little")


class CompanionLink:
    def __init__(self, device="/dev/serial0", baud=921600, fc_sysid=1, leds=None):
        self.mav = mavutil.mavlink_connection(
            device, baud=baud,
            source_system=fc_sysid,
            source_component=mavutil.mavlink.MAV_COMP_ID_ONBOARD_COMPUTER)
        self.leds = leds
        self.ready = False
        self.fc_mode = None
        self.fc_armed = False
        self._last_hb_sent = 0.0
        self._last_fc_hb = 0.0
        self.signing_key = load_signing_key()
        self.signing = False

    def wait_for_fc(self, timeout=None):
        """Block until the flight controller's heartbeat arrives, sending ours meanwhile."""
        start = time.monotonic()
        while self._last_fc_hb == 0.0:
            self.tick()
            if timeout is not None and time.monotonic() - start > timeout:
                raise TimeoutError("no heartbeat from flight controller")
            time.sleep(0.05)

    def set_ready(self, ready):
        self.ready = bool(ready)
        self._send_heartbeat()

    def fc_alive(self, max_age=3.0):
        return time.monotonic() - self._last_fc_hb < max_age

    def pilot_has_control(self):
        """True when the FC is in a pilot mode (Loiter, AltHold, RTL, ...), not GUIDED/AUTO."""
        return self.fc_mode not in COMPANION_MODES

    def tick(self):
        now = time.monotonic()
        if now - self._last_hb_sent >= HEARTBEAT_PERIOD_S:
            self._send_heartbeat()
        while True:
            msg = self.mav.recv_match(blocking=False)
            if msg is None:
                break
            if msg.get_type() == "BAD_DATA":
                continue
            if self.leds is not None:
                self.leds.on_message(msg, now)
            if (msg.get_type() == "HEARTBEAT"
                    and msg.get_srcComponent() == mavutil.mavlink.MAV_COMP_ID_AUTOPILOT1):
                self.fc_mode = msg.custom_mode
                self.fc_armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                self._last_fc_hb = now
                if self.signing_key and not self.signing:
                    self._start_signing(signed_timestamp(msg.get_msgbuf()))
        if self.leds is not None:
            self.leds.update(now)

    def _start_signing(self, fc_timestamp):
        # Start just after the FC's own timestamp: the Pi has no RTC and may boot
        # with a stale clock in the field, and the FC rejects timestamps far behind its own.
        self.mav.setup_signing(
            self.signing_key, sign_outgoing=True,
            allow_unsigned_callback=lambda _mav, _msgid: True,  # FC may not have a key yet
            initial_timestamp=None if fc_timestamp is None else fc_timestamp + 1,
            link_id=SIGNING_LINK_ID)
        self.signing = True
        print(f"MAVLink signing on (timestamp from {'FC' if fc_timestamp else 'Pi clock'})", flush=True)

    def _send_heartbeat(self):
        status = (mavutil.mavlink.MAV_STATE_ACTIVE if self.ready
                  else mavutil.mavlink.MAV_STATE_STANDBY)
        self.mav.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
            0, 0, status)
        self._last_hb_sent = time.monotonic()
        if self.leds is not None:
            self.leds.on_sent(self._last_hb_sent)

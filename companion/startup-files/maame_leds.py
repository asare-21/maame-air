#!/usr/bin/env python3
"""Drives the five Pi-controlled status LEDs on the Maame carrier board.

All LEDs are active high (GPIO -> resistor -> LED -> GND):
    GPIO16  PI     green   on while the companion script runs (blinks if the FC goes quiet)
    GPIO20  DATA   yellow  flashes on each MAVLink message to or from the FC
    GPIO19  B-H    green   battery high
    GPIO21  B-M    yellow  battery mid
    GPIO18  B-L    red     battery low (flashes when the FC reports a low-battery failsafe)

Battery level comes from the FC over MAVLink: SYS_STATUS.battery_remaining (%)
when the FC reports it, otherwise SYS_STATUS.voltage_battery per cell. The pack
is a 6S Li-ion. BATTERY_STATUS.charge_state LOW or worse makes B-L flash.

CompanionLink (maame_ready.py) calls on_message() for every message it reads and
on_sent() for every message it sends, plus update() once per loop.
"""
import time

CELLS = 6
PCT_HIGH = 50          # >= this: B-H
PCT_MID = 25           # >= this: B-M, below: B-L
CELL_V_HIGH = 3.70     # voltage fallback, per cell
CELL_V_MID = 3.50
DATA_FLASH_S = 0.08   # long enough to see at a 20 Hz main loop
FC_QUIET_S = 3.0
BLINK_PERIOD_S = 0.5
CHARGE_STATE_LOW = 2   # MAV_BATTERY_CHARGE_STATE_LOW
VOLT_SMOOTHING = 0.1   # per SYS_STATUS (1 Hz default): ~10 s time constant

PIN_PI, PIN_DATA, PIN_BH, PIN_BM, PIN_BL = 16, 20, 19, 21, 18


def battery_level(remaining_pct, voltage_mv):
    """Return 'high', 'mid', 'low' or None (no data)."""
    if remaining_pct is not None and 0 <= remaining_pct <= 100:
        if remaining_pct >= PCT_HIGH:
            return "high"
        return "mid" if remaining_pct >= PCT_MID else "low"
    if voltage_mv:
        cell = voltage_mv / 1000.0 / CELLS
        if cell > CELL_V_HIGH:
            return "high"
        return "mid" if cell >= CELL_V_MID else "low"
    return None


class StatusLeds:
    def __init__(self, led_factory=None):
        if led_factory is None:
            from gpiozero import LED
            led_factory = LED
        self.pi, self.data, self.bh, self.bm, self.bl = (
            led_factory(p) for p in (PIN_PI, PIN_DATA, PIN_BH, PIN_BM, PIN_BL))
        self.level = None
        self.failsafe = False
        self._data_until = 0.0
        self._last_fc_msg = 0.0
        self._volt_mv = None

    def on_message(self, msg, now=None):
        now = time.monotonic() if now is None else now
        self._flash_data(now)
        if msg.get_srcComponent() == 1:  # MAV_COMP_ID_AUTOPILOT1
            self._last_fc_msg = now
        kind = msg.get_type()
        if kind == "SYS_STATUS":
            remaining = msg.battery_remaining if msg.battery_remaining >= 0 else None
            voltage = msg.voltage_battery if 0 < msg.voltage_battery < 65535 else None
            if voltage is not None:
                # smooth throttle sag so the LEDs don't flicker between levels
                self._volt_mv = voltage if self._volt_mv is None else (
                    self._volt_mv + VOLT_SMOOTHING * (voltage - self._volt_mv))
            self.level = battery_level(remaining, self._volt_mv)
        elif kind == "BATTERY_STATUS" and msg.id == 0:
            self.failsafe = getattr(msg, "charge_state", 0) >= CHARGE_STATE_LOW

    def on_sent(self, now=None):
        self._flash_data(time.monotonic() if now is None else now)

    def update(self, now=None):
        now = time.monotonic() if now is None else now
        blink_on = int(now / BLINK_PERIOD_S) % 2 == 0
        fc_ok = now - self._last_fc_msg < FC_QUIET_S
        self._set(self.pi, True if fc_ok else blink_on)
        self._set(self.data, now < self._data_until)
        self._set(self.bh, self.level == "high")
        self._set(self.bm, self.level == "mid")
        low = self.level == "low" or self.failsafe
        self._set(self.bl, low and (blink_on if self.failsafe else True))

    def off(self):
        for led in (self.pi, self.data, self.bh, self.bm, self.bl):
            led.off()

    def _flash_data(self, now):
        self._data_until = now + DATA_FLASH_S

    @staticmethod
    def _set(led, on):
        led.on() if on else led.off()

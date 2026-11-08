"""
Pi health for the ground station: CompanionLink sends these as MAVLink
NAMED_VALUE_FLOAT from component 191 every few seconds, and the GCS companion
panel shows them (and blocks launch on under-voltage or overheating).

  PI_TEMP    CPU temperature, deg C
  PI_LOAD    1-minute load average
  PI_WIFI    Wi-Fi signal, dBm (0 = not associated, e.g. hotspot mode)
  PI_THROT   vcgencmd get_throttled bits (-1 = unknown):
             bit 0 under-voltage now, 1 freq capped, 2 throttled, 3 soft temp limit;
             bits 16-19 = the same "has happened since boot"
  PI_ROUTER  1 when mavlink-routerd is running
  PI_CAM     1 when the camera stream (mediamtx) is running

Every reader returns a fallback instead of raising: health reporting must
never stop the arming-gate heartbeat.
"""
import os
import subprocess

THERMAL = "/sys/class/thermal/thermal_zone0/temp"
WIRELESS = "/proc/net/wireless"
THROTTLED_SYSFS = "/sys/devices/platform/soc/soc:firmware/get_throttled"


def parse_wireless(text, iface="wlan0"):
    """Signal level in dBm for iface from /proc/net/wireless, 0.0 when absent."""
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        if name.strip() == iface and rest:
            fields = rest.split()
            if len(fields) >= 3:
                return float(fields[2].rstrip("."))
    return 0.0


def parse_throttled(text):
    """Bits from 'throttled=0x50000' (vcgencmd) or '50000' (sysfs); -1 when unreadable."""
    value = text.strip().split("=")[-1].strip()
    try:
        return int(value, 16)
    except ValueError:
        return -1


def _read(path):
    with open(path) as f:
        return f.read()


def cpu_temp_c():
    try:
        return int(_read(THERMAL).strip()) / 1000.0
    except (OSError, ValueError):
        return -1.0


def wifi_dbm():
    try:
        return parse_wireless(_read(WIRELESS))
    except OSError:
        return 0.0


def throttled():
    try:
        return parse_throttled(_read(THROTTLED_SYSFS))
    except OSError:
        pass
    try:
        out = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=1)
        return parse_throttled(out.stdout)
    except (OSError, subprocess.SubprocessError):
        return -1


def process_running(name):
    try:
        pids = os.listdir("/proc")
    except OSError:
        return False
    for pid in pids:
        if pid.isdigit():
            try:
                if _read(f"/proc/{pid}/comm").strip() == name:
                    return True
            except OSError:
                continue
    return False


def read_status():
    """Name -> value, names at most 10 chars (NAMED_VALUE_FLOAT limit)."""
    return {
        "PI_TEMP": cpu_temp_c(),
        "PI_LOAD": os.getloadavg()[0],
        "PI_WIFI": wifi_dbm(),
        "PI_THROT": float(throttled()),
        "PI_ROUTER": 1.0 if process_running("mavlink-routerd") else 0.0,
        "PI_CAM": 1.0 if process_running("mediamtx") else 0.0,
    }


if __name__ == "__main__":
    for k, v in read_status().items():
        print(f"{k:10} {v}")

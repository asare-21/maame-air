"""Run: python3 -m unittest test_maame_status (from companion/startup-files)."""
import unittest

from maame_status import parse_throttled, parse_wireless, read_status

WIRELESS = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
 wlan0: 0000   54.  -56.  -256        0      0      0      0      0        0
"""


class StatusParsers(unittest.TestCase):
    def test_wifi_signal(self):
        self.assertEqual(parse_wireless(WIRELESS), -56.0)
        self.assertEqual(parse_wireless(WIRELESS, "wlan1"), 0.0)
        self.assertEqual(parse_wireless(WIRELESS.splitlines()[0]), 0.0)  # hotspot: no wlan0 line

    def test_throttled_bits(self):
        self.assertEqual(parse_throttled("throttled=0x50005\n"), 0x50005)
        self.assertEqual(parse_throttled("0\n"), 0)
        self.assertEqual(parse_throttled("error"), -1)

    def test_read_status_never_raises_and_names_fit_mavlink(self):
        status = read_status()  # also off-Pi, where /proc and /sys are missing
        self.assertEqual(set(status), {"PI_TEMP", "PI_LOAD", "PI_WIFI", "PI_THROT", "PI_ROUTER", "PI_CAM"})
        self.assertTrue(all(len(k) <= 10 for k in status))


if __name__ == "__main__":
    unittest.main()

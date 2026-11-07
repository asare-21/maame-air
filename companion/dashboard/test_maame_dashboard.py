"""Run: python3 -m unittest test_maame_dashboard (from companion/dashboard)."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from maame_dashboard import apply_message, make_handler, new_state, pin_ok, snapshot


class Msg:
    def __init__(self, type_, sysid=1, compid=1, **fields):
        self._t, self._s, self._c = type_, sysid, compid
        self.__dict__.update(fields)

    def get_type(self): return self._t
    def get_srcSystem(self): return self._s
    def get_srcComponent(self): return self._c


class State(unittest.TestCase):
    def test_folds_fc_pi_and_position_messages(self):
        st = new_state()
        apply_message(st, Msg("HEARTBEAT", custom_mode=17, base_mode=128 | 1, system_status=4), 10.0)
        apply_message(st, Msg("HEARTBEAT", compid=191, custom_mode=0, base_mode=0, system_status=4), 10.0)
        apply_message(st, Msg("SYS_STATUS", voltage_battery=22680, battery_remaining=-1), 10.0)
        apply_message(st, Msg("HOME_POSITION", latitude=516500000, longitude=-8000000), 10.0)
        apply_message(st, Msg("GLOBAL_POSITION_INT", lat=516509000, lon=-8000000, relative_alt=12500), 10.0)
        s = snapshot(st, 11.0)
        self.assertEqual((s["mode"], s["armed"], s["fc_online"], s["pi_online"], s["pi_active"]), ("BRAKE", True, True, True, True))
        self.assertEqual((s["volts"], s["battery_pct"], s["alt_m"]), (22.68, None, 12.5))
        self.assertAlmostEqual(s["home_dist_m"], 100.1, delta=0.5)  # 0.0009 deg of latitude
        self.assertFalse(snapshot(st, 20.0)["fc_online"])  # 10 s without a heartbeat

    def test_pin(self):
        self.assertTrue(pin_ok("4821", "4821"))
        self.assertFalse(pin_ok("0000", "4821"))
        self.assertFalse(pin_ok(None, "4821"))
        self.assertFalse(pin_ok("", ""))  # no PIN configured never means open


class FakeLink:
    def __init__(self): self.sent = []
    def snapshot(self): return {"mode": "AUTO"}
    def send_action(self, a): self.sent.append(a)


class Http(unittest.TestCase):
    def setUp(self):
        self.link = FakeLink()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.link, "4821"))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def req(self, path, pin=None, body=None):
        r = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                   headers={"X-Maame-Pin": pin} if pin else {})
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_page_and_state_need_the_pin(self):
        self.assertEqual(self.req("/")[0], 200)
        self.assertEqual(self.req("/api/state")[0], 401)
        self.assertEqual(self.req("/api/state", "1111")[0], 401)
        code, body = self.req("/api/state", "4821")
        self.assertEqual((code, json.loads(body)), (200, {"mode": "AUTO"}))

    def test_only_pause_rtl_land_with_the_right_pin(self):
        self.assertEqual(self.req("/api/cmd", "1111", {"action": "land"})[0], 401)
        self.assertEqual(self.req("/api/cmd", "4821", {"action": "arm"})[0], 400)
        self.assertEqual(self.req("/api/cmd", "4821", {"action": "rtl"})[0], 200)
        self.assertEqual(self.link.sent, ["rtl"])


if __name__ == "__main__":
    unittest.main()

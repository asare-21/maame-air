# Ground station: flying Maame with MaameDrone-ArduDeck

Maame flies autonomous missions with **no RC transmitter**. The laptop app
(MaameDrone-ArduDeck, the `maame` branch of the ArduDeck fork) is the pilot; the
Pi companion and the flight controller's failsafes are the safety net.

## Links

| Link | Path | Notes |
|---|---|---|
| Wi-Fi | laptop ⇄ Pi `maame.local:14550` (mavlink-router) ⇄ FC UART1 | Pi joins a known network, or after 60 s starts the open hotspot `Maame-B412` (10.42.0.1) |
| 4G (optional) | laptop ⇄ Tailscale ⇄ Pi, same port | needs the LTE modem: `companion/4g/install-4g.sh`; **signing required** |
| SiK radio | laptop USB radio ⇄ FC UART4, 57600 | independent of the Pi: still works if the Pi dies |

The app receives on every link and **transmits on one**, best first
(Wi-Fi → 4G → SiK); it switches after 3 s of silence and returns once the better
link has been steady for 5 s. The link badge in the header shows which is active.

## Connect

Connection panel → **Single vehicle** → **Maame drone** card → choose the SiK
port (optional), type the 4G address (optional) → **Connect to Maame**.

!!! warning
    A link opened on the **Multi-vehicle** tab is not the Maame connection: the
    launch controls stay disabled and the emergency bar does not appear. Remove it
    there and use *Connect to Maame*.

## Pre-flight Checks panel

Telemetry view → Workspace → Add panel → **Pre-flight Checks**. From the top:

1. **Maame safety baseline (no RC)** – the FC's failsafe/fence/gate settings
   against the Maame baseline; *Apply* fixes them (some need a reboot).
2. **Maame Pi companion** – gate state, Pi CPU temperature, load, Wi-Fi signal,
   router, power (under-voltage), link signing, and the **arming gate script**
   version with *Install/Reinstall* (uploads the Lua and reboots the FC).
3. **Maame autonomous launch** – the ready checklist, then
   **1. Upload mission → 2. Pi ready → 3. Arm and start mission**.
   The checklist blocks launch on: no Maame link, unsafe settings, GPS (3D fix,
   8+ satellites), battery below the FC's `BATT_ARM_VOLT`, Pi offline /
   under-voltage / ≥ 80 °C, FC pre-arm failures, mission not uploaded, or a
   mission that breaks the fence or needs more than 70 % of the 10 Ah pack.
4. **Maame hover test** – take off, hover at 0.5 or 1 m for 5–10 s, land on the
   spot. ArduPilot takes off to at least 1 m first. Replaces the mission on the FC.
5. **Mission from coordinates** – paste or load a CSV, one point per line:
   `lat, lon[, altitude m[, hover s]]`; optional take-off first and RTL last.

## In flight

While armed the header shows **Pause** (BRAKE: holds position), **Resume** (AUTO),
**RTL**, **Land**, and **Hold to kill motors** (1.5 s; the drone falls).
Shortcuts: Shift+P / Shift+A / Shift+R / Shift+L (no shortcut for the kill).

If every link is lost in AUTO the FC **continues the mission** (and then lands /
returns as the mission says); low battery → RTL, critical → land; fence breach → RTL.

## Phone or tablet

The Pi serves a dashboard at **http://maame.local:8080** (hotspot:
`http://10.42.0.1:8080`): mode, battery, GPS, height, distance home, mission step,
Pi state, messages, and **Pause / Return home / Land** only. It never sends
heartbeats, so it cannot hide a lost laptop from the FC. Install once:

```
scp -r companion/dashboard maame@maame.local:~/
ssh -t maame@maame.local 'sudo bash ~/dashboard/install-dashboard.sh'
```

It prints a 6-digit PIN once (later: `sudo cat /etc/maame/dashboard-pin`).

## Flight logs

* **Telemetry logs:** every *Connect to Maame* session is recorded to
  `Documents/MaameDrone/flight-logs/maame-<date>_<time>.tlog` (button *Open flight
  logs* on the connect card). Open them in MAVExplorer or Mission Planner.
* **FC logs (DataFlash):** Logs view → list → download after landing.

## Turning on MAVLink signing

Do this before flying outdoors: the hotspot is open, and without signing anyone
on it could command the drone. The Pi already has a key.

1. Show the Pi's key: `ssh -t maame@maame.local 'sudo cat /etc/maame/mavlink-signing.key'`
   (64 hex characters; treat it like a password).
2. ArduDeck → **Settings → Signing** → paste the key → save.
3. Connect to Maame (drone disarmed) → **Send to FC**.
4. Restart the Pi companion so it signs from its first packet:
   `ssh -t maame@maame.local 'sudo systemctl restart maame-startup'`.
5. Check: companion card **Link signing: ON**, **Pi ready** opens the gate.

If the keys ever differ, the Pi cannot open the gate (arming stays blocked) and
the app's commands are ignored. Recovery: connect the FC by **USB** (always
accepts unsigned) and send the right key, or clear signing there.
The 4G link refuses to fly until signing is on.

## Camera

With a Pi Camera Module 3 Wide on the Pi's CSI port:

```
scp -r companion/camera maame@maame.local:~/
ssh -t maame@maame.local 'cd ~/camera && sudo ./install-camera.sh'
```

Then ArduDeck → Camera panel → source **Maame Pi camera (Wi-Fi)**
(`rtsp://maame.local:8554/cam`, 720p, 1.5 Mbit/s). The stream runs at low CPU
priority so it can never starve the companion.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| "No flight controller connected" on Install gate | connected through a Multi-vehicle link: use *Connect to Maame* |
| Wi-Fi connects but nothing updates after a Pi reboot | fixed (the app now speaks first); update the app |
| Pi companion "no heartbeat" | companion service down: `systemctl status maame-startup` on the Pi |
| Battery check red at ~22.7 V | below `BATT_ARM_VOLT` 22.8 V: charge the pack |
| Gate never opens after Pi ready | signing key mismatch between Pi and FC (see above), or the Pi refused (its message says why) |
| GPS "no fix" with the module blinking | data not reaching the FC: check the J1 joints are soldered, not pushed on |

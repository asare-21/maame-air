# Maame carrier rev A: assembly notes

## What JLCPCB fits
All SMD parts, plus the four Kakute headers (through-hole):
- J1: 2x9 male header, 2.54 mm (LCSC C42372517)
- J23, J24, J25: 1x4 male headers, 2.54 mm (LCSC C32713270)

Everything else marked DNP (other headers, Pi 2x20 socket, JST-XH outputs J20/J21/J22, wire pads J3) is hand-soldered.

## Kakute harness (J1, J23, J24, J25)
The Kakute pads are flat solder pads, so the Kakute does not plug straight onto the carrier.
Make one short harness instead:
1. Solder thin silicone wires (26-28 AWG) to the Kakute pads.
2. Crimp the other ends into 2.54 mm Dupont housings that match the carrier headers pin for pin:
   - J1 (2x9): Kakute left pad strip. Outer column = B+, GND, R3, GND, R4, SDA, R6, RSI, GND; inner column = Vo, GND, T3, 5V, T4, SCL, T6, 5V, 3V3.
     **B+ and Vo: do not wire** (no net on the carrier).
   - J23 (1x4): Kakute top pads G, 5V, Vi, CAM. **Vi and CAM: do not wire.**
   - J24 (1x4): Kakute bottom pads Z-, 5V, G, LED.
   - J25 (1x4): Kakute 6-pin JST 9V, T1, R1, G.
3. Keep the wires slack so the Kakute stays soft-mounted on its grommets.
Pin 1 of each header is the square pad; every pin is labelled on the silkscreen.

## Power
- Battery: 6S Li-ion / LiPo only, 18-25.2 V (22.2 V nominal), into J3.
- J3 wire: 18 AWG (16 AWG if VBAT OUT on J20 is loaded near 2 A). It can carry about 4.6 A with everything at full load.
- F1 3 A PTC feeds the 5 V (U2) and 12 V (U3) regulators. F2 2 A PTC feeds J20 VBAT OUT.

## Mechanical
- Frame: 4x M2.5 slots on a 48.5 mm square, standoffs at least 10 mm. Trim leads to 1.5 mm or less underneath.
- Pi Zero: standard-height 2x20 socket (8.5 mm), so the 12 V regulator under the Pi clears it.

## First power-up (bench supply, about 20 V, current limited, nothing plugged in)
1. 5V_AUX on J6/J13: 5.0-5.1 V, AUX5V LED on.
2. 12V_AUX on J22: 12.0 V, 12V LED on.
3. Only then plug in the Kakute harness, the Pi and the peripherals.

Not yet confirmed: Kakute pad pitch (check against the 1:1 template), Kakute 5 V / 9 V current limits,
SiK and TF-Luna lead order, M10Q lead colours.

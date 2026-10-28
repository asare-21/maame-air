# MaameDrone V1.0: assembly notes

## What JLCPCB fits
All SMD parts, plus these through-hole parts:
- J1: 2x9 male header, 2.54 mm (LCSC C42372517)
- J23, J24, J25: 1x4 male headers, 2.54 mm (LCSC C32713270)
- U1: Pi socket, 2x20 female header, 2.54 mm, 8.5 mm tall (LCSC C5124634)

Everything else (peripheral headers J6-J13, J17, J18, J7, JST-XH output J20, wire pads J3) is left out of the BOM/CPL and hand-soldered.
In JLC's placement preview, check the headers sit square on their holes (the CPL gives each header's centre).

## Pi Zero W
The Pi plugs straight onto U1, component side up (chips facing up, SD card on the left, USB/HDMI at the rear).
Solder a 2x20 male header on the Pi's UNDERSIDE: push the short ends up through the holes from below, so the
plastic spacer and the long pins are under the Pi, and solder on the top (component) side. The pins then point down into U1.
**Do not use a Pi Zero WH** (factory header on top, pins pointing up): it would have to go in upside down, which
mirrors the pinout and puts 3V3/5V on the wrong pins.

## Kakute harness (J1, J23, J24, J25)
The Kakute pads are flat solder pads, so the Kakute does not plug straight onto the carrier.
Make one short harness instead:
1. Solder thin silicone wires (26-28 AWG) to the Kakute pads.
2. Crimp the other ends into 2.54 mm Dupont housings that match the carrier headers pin for pin:
   - J1 (2x9): Kakute left pad strip. Outer column = B+, GND, R3, GND, R4, SDA, R6, RSI, GND; inner column = Vo, GND, T3, 5V, T4, SCL, T6, 5V, 3V3.
     **B+ and Vo: do not wire** (no net on the carrier).
   - J23 (1x4): Kakute top pads G, 5V, Vi, CAM. **Vi and CAM: do not wire.**
   - J24 (1x4): Kakute bottom pads Z-, 5V, G, LED.
   - J25 (1x4): Kakute 6-pin JST 9V, T1, R1, G. **9V: do not wire** (pin 1 has no net).
3. Keep the wires slack so the Kakute stays soft-mounted on its grommets.
Pin 1 of each header is the square pad; every pin is labelled on the silkscreen.

## Power
- Battery: 6S Li-ion / LiPo only, 18-25.2 V (22.2 V nominal), into J3.
- J3 wire: 18 AWG. Worst case about 3.1 A (5 V buck at 3.5 A out from a flat 18 V pack = 1.1 A, plus 2 A on J20 VBAT OUT).
- F1 2 A PTC feeds the 5 V regulator (U2). F2 2 A PTC feeds J20 VBAT OUT.
- No 12 V or 9 V outputs on this board (removed to cut assembly cost).

## Mechanical
- Frame: 4x M2.5 slots on a 48.5 mm square, standoffs at least 10 mm. Trim leads to 1.5 mm or less underneath.
- Pi Zero: standard-height 2x20 socket (8.5 mm).

## First power-up (bench supply, about 20 V, current limited, nothing plugged in)
1. 5V_AUX on J6/J13: 5.0-5.1 V, AUX5V LED on.
2. Only then plug in the Kakute harness, the Pi and the peripherals.

Not yet confirmed: Kakute pad pitch (check against the 1:1 template), Kakute 5 V current limit,
SiK and TF-Luna lead order, M10Q lead colours.

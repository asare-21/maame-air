# MaameDrone V1.0 carrier board

MaameDrone V1.0 is a 95 x 116.5 mm, two-layer carrier board for a 6S drone. It holds:

- a **Holybro Kakute H7** flight controller on M2.5 grommets, wired through a short Dupont harness,
- a **Raspberry Pi Zero W**, which plugs **face down** onto a 2x20 socket,
- a **5 V, 3.5 A buck regulator** (TI TPS54360B) that runs from the battery,
- headers for GPS, a SiK radio, an iBUS receiver, a TF-Luna rangefinder, a servo, spare I2C/SPI, and a fused VBAT output.

![MaameDrone V1.0, 3D view](img/render_3d_angle.png)

## Key facts

| | |
|---|---|
| Battery | 6S Li-ion / LiPo only, 18-25.2 V (22.2 V nominal), into the J3 pads |
| 5 V rail (5V_AUX) | TPS54360B buck, 3.5 A, fed through F1 (2 A PTC) and D9 (TVS) |
| VBAT OUT (J20) | battery voltage through F2 (2 A PTC), 2-pin JST-XH, pin 1 = + |
| Frame mount | 4x M2.5 slots on a 48.5 mm square, standoffs at least 10 mm |
| Assembly | JLCPCB fits the 32 SMD parts; every through-hole part is hand-soldered |

The board has no 12 V or 9 V outputs (they were removed to cut assembly cost).

## Where to start

- [Board tour](board.md): every connector, pin and LED, with board images.
- [Assembly](assembly.md): parts to buy, Pi orientation, the Kakute harness and first power-up.
- [Fabrication files](fabrication.md): Gerbers, BOM, CPL, schematic and the 1:1 template.

# Fabrication files

## Downloads

| File | What it is |
|---|---|
| [Gerbers (zip)](files/MaameDrone_V1.0_gerbers.zip) | Gerbers and drill files to upload to JLCPCB |
| [JLC BOM](files/MaameDrone_V1.0_BOM_JLC.csv) | SMD parts JLCPCB fits: 32 parts on 21 lines, all with LCSC numbers |
| [JLC CPL](files/MaameDrone_V1.0_CPL_JLC.csv) | pick-and-place positions for the SMD parts |
| [Hand-solder BOM](files/MaameDrone_V1.0_BOM_hand_solder.csv) | through-hole parts to buy and solder yourself |
| [Schematic (PDF)](files/maame_carrier_schematic.pdf) | full schematic |
| [Renders (PDF)](files/MaameDrone_V1.0_renders.pdf) | top, bottom and 3D renders |
| [1:1 plate template (PDF)](files/maame_carrier_plate_template_1to1.pdf) | print at 100 % to check the Kakute pad pitch and frame holes |

## Ordering at JLCPCB

1. Upload the Gerber zip.
2. Turn on PCB assembly (top side) and upload the JLC BOM and CPL.
3. JLCPCB fits only the SMD parts (U2, L1, D1-D9, F1, F2, C1-C8, R1-R11). The through-hole parts are not in the BOM/CPL, even though they show in JLC's 3D view; buy them from the [hand-solder list](assembly.md#parts-to-buy-and-hand-solder).

## Rebuilding the files

The design is in KiCad: `maame_carrier.kicad_sch` and `maame_carrier.kicad_pcb`.

- `fab/make_jlc_files.py` rebuilds the JLC BOM and CPL from the schematic LCSC fields and a KiCad position file (`fab/pos_raw.csv`). Run it from the repo root.
- `fab/tht_centroids.py` (run with KiCad's Python) writes pad-centre positions for the through-hole headers to `fab/tht_centroids.json`, which `make_jlc_files.py` uses.
- `plate_template/make_template.py` builds the 1:1 plate template board.

The images on this site are the renders in `fab/`. Regenerate those and the site picks them up on the next build.

# JLC wants part centroids in the CPL; KiCad header footprints have their origin on pin 1. Write pad-centre overrides for the THT headers.
import pcbnew, json
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb'); mm = pcbnew.ToMM
out = {}
for f in b.GetFootprints():
    if f.GetReference() in ("J1", "J23", "J24", "J25", "U1") and not f.IsDNP():
        pads = [p for p in f.Pads() if p.GetNumber().isdigit() and int(p.GetNumber()) <= 40]
        xs = [mm(p.GetPosition().x) for p in pads]; ys = [mm(p.GetPosition().y) for p in pads]
        out[f.GetReference()] = [round((min(xs) + max(xs)) / 2, 4), round((min(ys) + max(ys)) / 2, 4)]
json.dump(out, open('fab/tht_centroids.json', 'w'), indent=0); print(out)

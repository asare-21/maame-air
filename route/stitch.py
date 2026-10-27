# GND stitching vias on a 5 mm grid wherever both GND pours are solid around the via; islands removed.
import pcbnew, math
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb')
gnd = b.FindNet('/GND')
zones = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == '/GND'}
for z in zones.values(): z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
P = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
def solid(x, y, r=0.75):
    pts = [(x, y)] + [(x + r * math.cos(a), y + r * math.sin(a)) for a in [k * math.pi / 4 for k in range(8)]]
    return all(z.HitTestFilledArea(l, P(px, py), 0) for l, z in zones.items() for px, py in pts)
n = 0
for gx in range(3, 95, 10):
    for gy in range(3, 117, 10):
        if solid(gx, gy) and all(math.hypot(pcbnew.ToMM(pad.GetPosition().x) - gx, pcbnew.ToMM(pad.GetPosition().y) - gy) > 2.0 for f in b.GetFootprints() for pad in f.Pads()):
            v = pcbnew.PCB_VIA(b); v.SetPosition(P(gx, gy)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
            v.SetNet(gnd); b.Add(v); n += 1
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save('maame_carrier.kicad_pcb'); print('stitching vias', n)

# Import Freerouting result, add GND pours on both layers, fill.
import pcbnew, sys
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb')
assert pcbnew.ImportSpecctraSES(b, 'route/maame_carrier.ses')
gnd = b.FindNet('/GND'); W, H = 95.0, 116.5
for layer, name in ((pcbnew.F_Cu, 'GND_TOP'), (pcbnew.B_Cu, 'GND_BOT')):
    z = pcbnew.ZONE(b); z.SetLayer(layer); z.SetNet(gnd); z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in [(0, 0), (W, 0), (W, H), (0, H)]: ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetLocalClearance(pcbnew.FromMM(0.3)); z.SetMinThickness(pcbnew.FromMM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
    b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save('maame_carrier.kicad_pcb')
print('tracks', sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK'), 'vias', sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA'))

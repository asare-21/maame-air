# Switch-node copper (BEC_SW) on F.Cu: U2 pin 8, C4, D8 cathode, L1 pad 1. Replaces any thin autorouted SW tracks.
import pcbnew
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb')
sw = b.FindNet('/BEC_SW')
z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(sw); z.SetZoneName('BEC_SW'); z.SetAssignedPriority(2)
ol = z.Outline(); ol.NewOutline()
for x, y in [(25.6, 9.4), (27.5, 9.4), (27.5, 5.6), (30.7, 5.6), (30.7, 10.4), (34.6, 12.5), (36.5, 12.5), (36.5, 18.5),
             (34.6, 18.5), (34.6, 13.9), (30.2, 12.75), (27.3, 12.75), (27.3, 11.4), (25.6, 11.0)]:
    ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
z.SetLocalClearance(pcbnew.FromMM(0.3)); z.SetMinThickness(pcbnew.FromMM(0.25)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
b.Add(z)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save('maame_carrier.kicad_pcb'); print('SW zone added')

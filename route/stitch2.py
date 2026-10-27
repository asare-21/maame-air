# Solid zone connection for the 3 GND pads whose thermal spokes land on islands, then thin stitching to a 10 mm grid.
import pcbnew, sys
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb')
if sys.argv[1] == "pads":
    for f in b.GetFootprints():
        for p in f.Pads():
            if (f.GetReference(), p.GetNumber()) in {("U1", "20"), ("U1", "30"), ("J1", "4"), ("U1", "25"), ("J17", "4"), ("J1", "28"), ("U1", "6"), ("U2", "7"), ("U2", "9"), ("D8", "2"), ("C2", "2"), ("C3", "2"), ("C6", "2"), ("C7", "2"), ("D9", "2"), ("J1", "21"), ("J20", "2")}:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
else:
    mm = pcbnew.ToMM
    grid5 = {(x, y) for x in range(3, 95, 5) for y in range(3, 117, 5)}
    grid10 = {(x, y) for x in range(3, 95, 10) for y in range(3, 117, 10)}
    drop = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA' and t.GetNetname() == '/GND'
            and (round(mm(t.GetPosition().x), 3), round(mm(t.GetPosition().y), 3)) in grid5 - grid10]
    for v in drop: b.Remove(v)
    print('removed', len(drop))
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save('maame_carrier.kicad_pcb')

# Place the 12 V buck (mirror of the 5 V cluster, offset under the Pi), J21/J22 outputs, 12 V LED, new 3 A F1.
import pcbnew
FPL = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/'
b = pcbnew.LoadBoard('maame_carrier.kicad_pcb')
def net(n):
    x = b.FindNet(n)
    if x is None or x.GetNetname() != n:
        x = pcbnew.NETINFO_ITEM(b, n); b.Add(x)
    return x
DX, DY = 12.0, 89.7
C0603, R0603, C1210 = ("Capacitor_SMD", "C_0603_1608Metric"), ("Resistor_SMD", "R_0603_1608Metric"), ("Capacitor_SMD", "C_1210_3225Metric")
PARTS = [
 ("U3", ("Package_SO", "TI_SO-PowerPAD-8_ThermalVias"), 25.5, 14.0, 0, "TPS54360BDDAR 12V 2A buck",
  {"1": "/BEC12_BOOT", "2": "/VBAT_F", "3": "unconnected-(U3-EN-Pad3)", "4": "/BEC12_RT", "5": "/BEC12_FB", "6": "/BEC12_COMP", "7": "/GND", "8": "/BEC12_SW", "9": "/GND"}, True),
 ("C11", C0603, 25.5, 10.2, 0, "100nF 50V 0603 (12V BOOT)", {"1": "/BEC12_BOOT", "2": "/BEC12_SW"}, True),
 ("C9", C1210, 19.5, 18.6, 90, "2.2uF 100V X7R 1210 (12V VIN)", {"1": "/VBAT_F", "2": "/GND"}, True),
 ("C10", C1210, 19.0, 9.6, 0, "2.2uF 100V X7R 1210 (12V VIN)", {"1": "/VBAT_F", "2": "/GND"}, True),
 ("R12", R0603, 22.3, 20.8, 90, "162k 1% 0603 (12V RT, 600 kHz)", {"1": "/BEC12_RT", "2": "/GND"}, True),
 ("D10", ("Diode_SMD", "D_SMC"), 32.5, 7.6, 0, "B560C 60V 5A Schottky SMC", {"1": "/BEC12_SW", "2": "/GND"}, True),
 ("L2", ("Inductor_SMD", "L_Coilcraft_XAL6060-XXX"), 37.6, 15.6, 0, "22uH 5.9A Coilcraft XAL6060-223MEC", {"1": "/BEC12_SW", "2": "/12V_AUX"}, True),
 ("C14", C1210, 44.2, 9.6, 90, "22uF 25V X7R 1210 (12V OUT)", {"1": "/12V_AUX", "2": "/GND"}, True),
 ("C15", C1210, 44.2, 20.4, 90, "22uF 25V X7R 1210 (12V OUT)", {"1": "/12V_AUX", "2": "/GND"}, True),
 ("R13", R0603, 30.2, 19.2, 0, "9.1k 1% 0603 (12V COMP)", {"1": "/BEC12_COMP", "2": "/BEC12_COMP_RC"}, True),
 ("C12", C0603, 30.2, 21.4, 0, "15nF 50V 0603 (12V COMP)", {"1": "/BEC12_COMP_RC", "2": "/GND"}, True),
 ("C13", C0603, 26.6, 21.4, 0, "56pF 50V C0G 0603 (12V COMP)", {"1": "/BEC12_COMP", "2": "/GND"}, True),
 ("R14", R0603, 33.8, 21.4, 0, "140k 1% 0603 (12V FB top)", {"1": "/12V_AUX", "2": "/BEC12_FB"}, True),
 ("R15", R0603, 37.4, 21.4, 0, "10k 1% 0603 (12V FB bottom)", {"1": "/BEC12_FB", "2": "/GND"}, True),
 # not offset (absolute positions)
 ("J21", ("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"), 4.6, 96.0, 0, "9V OUT from Kakute VTX 9V (JST-XH)", {"1": "/9V_FC", "2": "/GND"}, False),
 ("J22", ("Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical"), 4.6, 104.0, 0, "12V OUT 2A (JST-XH)", {"1": "/12V_AUX", "2": "/GND"}, False),
 ("D11", ("LED_SMD", "LED_0805_2012Metric_Pad1.15x1.40mm_HandSolder"), 12.4, 103.4, 90, "Green 0805: 12V_AUX on", {"1": "/GND", "2": "/LED11_A"}, False),
 ("R16", ("Resistor_SMD", "R_0805_2012Metric_Pad1.20x1.40mm_HandSolder"), 12.4, 107.4, 90, "2.2k 0805 (12V LED)", {"1": "/12V_AUX", "2": "/LED11_A"}, False),
 ("F1", ("Fuse", "Fuse_2920_7451Metric"), 12.1, 14.05, 0, "PTC fuse 2920 30V 3A hold 6A trip (BSMD2920-300-30V, LCSC C7190311)", {"1": "/VBAT", "2": "/VBAT_F"}, False),
]
for ref, (lib, name), x, y, rot, val, nets, offset in PARTS:
    fp = pcbnew.FootprintLoad(FPL + lib + '.pretty', name)
    fp.SetFPIDAsString(f'{lib}:{name}'); fp.SetReference(ref); fp.SetValue(val); fp.Reference().SetVisible(False)
    if offset: x, y = x + DX, y + DY
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))); fp.SetOrientationDegrees(rot)
    if ref in ("J21", "J22"): fp.SetDNP(True)
    for p in fp.Pads():
        if p.GetNumber() in nets: p.SetNet(net(nets[p.GetNumber()]))
    b.Add(fp)
b.Save('maame_carrier.kicad_pcb'); print('placed', len(PARTS))

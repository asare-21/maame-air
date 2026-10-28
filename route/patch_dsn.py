# Patch the KiCad DSN for Freerouting: net-class widths, 0.55 mm inset boundary, keep-outs round the frame slots and ESC slot.
import re, math, sys
p = sys.argv[1]; s = open(p).read()
W, H, R, INSET = 95.0, 116.5, 6.0, 0.55
um = lambda v: f"{v * 1000:.1f}"
# DSN y axis is negated (board y -> -y)
def rrect(x0, y0, x1, y1, r, n=8):
    pts = []
    for cx, cy, a0 in [(x1 - r, y0 + r, 270), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append(pts[0]); return pts
def path(pts): return " ".join(f"{um(x)} {um(-y)}" for x, y in pts)
b0 = s.index("(boundary"); b1 = s.index("\n    )", b0) + 6
s = s[:b0] + f"(boundary\n      (path pcb 0  {path(rrect(INSET, INSET, W - INSET, H - INSET, R - INSET))})\n    )" + s[b1:]
def circle(cx, cy, r, n=24): return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n + 1)]
def stadium(cx, cy, half, r, n=12):
    pts = [(cx + half + r * math.cos(math.radians(-90 + 180 * k / n)), cy + r * math.sin(math.radians(-90 + 180 * k / n))) for k in range(n + 1)]
    pts += [(cx - half + r * math.cos(math.radians(90 + 180 * k / n)), cy + r * math.sin(math.radians(90 + 180 * k / n))) for k in range(n + 1)]
    return pts + [pts[0]]
keep = [stadium(50.5, 47.6, 4.5, 2.5 + INSET)]                      # ESC cable slot
keep += [circle(x, y, 2.1 + 1.35 + INSET) for x in (23.25, 71.75) for y in (34.0, 82.5)]   # frame M2.5 slots + screw head/standoff
add = "".join(f'\n    (keepout "" (polygon signal 0  {path(k)}))' for k in keep)
i = s.index("(keepout"); s = s[:i] + add.lstrip("\n ") + "\n    " + s[i:]
# net classes: drop every class KiCad exported (it can emit merged ones like "Power,Default"), rebuild ours
blocks = list(re.finditer(r'\n    \(class .*?\n    \)(?=\n)', s, re.S))
assert blocks, "no net classes in DSN"
toks = []
for m in blocks:
    head = m.group(0)[:m.group(0).index("(circuit")]
    toks += re.findall(r'"[^"]*"|\S+', head)[2:]
for m in reversed(blocks): s = s[:m.start()] + s[m.end():]
PWR, GND, VB = {"/5V_AUX", "/5V_FC", "/BEC_SW"}, {"/GND"}, {"/VBAT", "/VBAT_F", "/VBAT_OUT_F"}
rest = sorted({t for t in toks if t not in PWR | GND | VB})
via = '(circuit\n        (use_via "Via[0-1]_600:300_um")\n      )\n'
def cls(name, nets, w, c): return f'\n    (class {name} {" ".join(nets)}\n      {via}      (rule\n        (width {w})\n        (clearance {c})\n      )\n    )'
k = s.index("\n  )\n  (wiring")
s = s[:k] + cls("kicad_default", rest, 250, 200) + cls("Power", sorted(PWR), 800, 250) + cls("Ground", sorted(GND), 500, 250) + cls("VBAT", sorted(VB), 800, 300) + s[k:]
open(p, "w").write(s)

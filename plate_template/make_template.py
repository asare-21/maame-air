# Build a 1:1 plate template copy of the board: shift onto the middle of an A4 page, add grid, check bar, nose arrow.
import re, sys, uuid
src, dst = sys.argv[1], sys.argv[2]
OX, OY, W, H = 57.5, 60, 95, 95
s = open(src).read()
# top-level coordinates only (two-tab depth); footprint children are local and move with their footprint
s = re.sub(r'(?m)^(\t\t\((?:at|start|end|mid|center) )([-\d.]+) ([-\d.]+)',
           lambda m: f'{m.group(1)}{float(m.group(2)) + OX:g} {float(m.group(3)) + OY:g}', s)
L = "Dwgs.User"
def line(x0, y0, x1, y1, w=0.1):
    return (f'\t(gr_line\n\t\t(start {x0:g} {y0:g})\n\t\t(end {x1:g} {y1:g})\n\t\t(stroke\n\t\t\t(width {w})\n'
            f'\t\t\t(type solid)\n\t\t)\n\t\t(layer "{L}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
def text(t, x, y, size=2.5, just=""):
    j = f'\n\t\t\t(justify {just})' if just else ''
    return (f'\t(gr_text "{t}"\n\t\t(at {x:g} {y:g} 0)\n\t\t(layer "{L}")\n\t\t(uuid "{uuid.uuid4()}")\n'
            f'\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n\t\t\t\t(thickness {size*0.15:g})\n\t\t\t){j}\n\t\t)\n\t)\n')
g = ""
for v in range(0, 100, 5):  # 5 mm grid over the board, heavier every 10 mm
    if v > W: break
    w = 0.15 if v % 10 == 0 else 0.05
    g += line(OX + v, OY, OX + v, OY + H, w) + line(OX, OY + v, OX + W, OY + v, w)
for v in range(0, 100, 10):  # axis labels in board mm
    g += text(str(v), OX + v, OY - 2.5, 1.8) + text(str(v), OX - 3.5, OY + v, 1.8)
# 50 mm check bar with 10 mm ticks
by = OY + H + 22
g += line(OX, by, OX + 50, by, 0.4)
for v in range(0, 51, 10):
    g += line(OX + v, by - 2, OX + v, by + 2, 0.3)
g += text("50 mm: measure this bar. If it is not exactly 50 mm, reprint at 100% / Actual size", OX - 2, by + 6, 2.2, "left")
# nose arrow above the board (top edge = nose = Kakute arrow)
ax, ay = OX + W / 2, OY - 7
g += line(ax, ay, ax, ay - 14, 0.5) + line(ax, ay - 14, ax - 3, ay - 10, 0.5) + line(ax, ay - 14, ax + 3, ay - 10, 0.5)
g += text("NOSE (Kakute arrow direction)", ax + 5, ay - 9, 2.5, "left")
g += text("Maame carrier 1:1 plate template. Board outline is a 95 x 95 mm placeholder.", 105, 14, 3)
g += text("Lay on the top plate, nose arrow to the front; poke through the holes you want; read positions off the grid (mm from top-left).", 105, 19.5, 2)
g += text("Kakute M3 holes, ESC slot and Pi outline are drawn where they sit now.", 105, 24, 2)
i = s.rindex('\t(embedded_fonts no)')
open(dst, "w").write(s[:i] + g + s[i:])

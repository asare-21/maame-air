# Build JLCPCB BOM + CPL from the schematic LCSC fields and the KiCad position file.
import csv, re, sys, collections
sch = open("maame_carrier.kicad_sch").read()
parts = {}
for m in re.finditer(r'\n\t\(symbol\n\t\t\(lib_id "[^"]+"\).*?\n\t\)(?=\n)', sch, re.S):
    b = m.group(0)
    prop = lambda k: (re.search(r'\(property "' + k + r'" "([^"]*)"', b) or [None, None])[1]
    if prop("LCSC") and "(dnp yes)" not in b and "(in_bom yes)" in b:
        parts[prop("Reference")] = (prop("Value"), prop("Footprint").split(":")[-1], prop("LCSC"))
groups = collections.defaultdict(list)
for ref, key in parts.items(): groups[key].append(ref)
nat = lambda r: (re.sub(r"\d", "", r), int(re.sub(r"\D", "", r)))
with open("fab/maame_carrier_BOM_JLC.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: nat(sorted(kv[1], key=nat)[0])):
        w.writerow([val, ",".join(sorted(refs, key=nat)), fp, lcsc])
rows = list(csv.DictReader(open("fab/pos_raw.csv")))
assert {r["Ref"] for r in rows} == set(parts), (sorted({r["Ref"] for r in rows} ^ set(parts)))
with open("fab/maame_carrier_CPL_JLC.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in sorted(rows, key=lambda r: nat(r["Ref"])):
        w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}mm', f'{float(r["PosY"]):.4f}mm', "Top", f'{float(r["Rot"]):g}'])
print(len(parts), "parts,", len(groups), "BOM lines")

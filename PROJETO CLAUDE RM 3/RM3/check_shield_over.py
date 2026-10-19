import csv
from build_shield import T

with open('lotes_p68/SHIELD.tsv', encoding='utf-8') as f:
    shields = list(csv.DictReader(f, delimiter='\t'))

over = []
for r in shields:
    rid = r['id']
    orig = r['original']
    mx = int(r['max_bytes'])
    tr, nt = T[rid]
    l = len(tr)
    if l > mx:
        over.append((rid, orig, mx, l, tr))

print(f"Total over: {len(over)}")
for rid, orig, mx, l, tr in over:
    print(f"{rid} (max {mx:2d}, was {l:2d}): {orig!r} -> {tr!r}")

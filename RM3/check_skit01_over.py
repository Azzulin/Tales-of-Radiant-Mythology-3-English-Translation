import csv
from build_skit01 import T

with open('lotes_p68/SKIT-01.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

over = []
for r in rows:
    rid = r['id']
    mx = int(r['max_bytes'])
    orig = r['original']
    tr = T[rid]
    if len(tr) > mx:
        over.append((rid, orig, mx, len(tr), tr))

print(f"Total over max_bytes: {len(over)}")
for rid, orig, mx, l, tr in over:
    print(f"{rid:8s} (max {mx:2d}, was {l:2d}): {orig!r} -> {tr!r}")

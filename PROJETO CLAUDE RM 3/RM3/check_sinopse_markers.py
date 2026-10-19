import csv, glob

total = 0
found = 0
for p in sorted(glob.glob('lotes_bancos/SINOPSE-*.tsv')):
    rows = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    total += len(rows)
    for r in rows:
        c = r['original'].count(chr(9675)*2)
        if c:
            found += 1
            print(f"{r['id']}: {c} in {repr(r['original'])}")
print(f"Total SINOPSE rows: {total}, with marker: {found}")

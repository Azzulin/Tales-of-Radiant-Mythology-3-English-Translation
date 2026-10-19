import csv

with open('lotes_p68/MISC.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

print(f"Total rows in MISC.tsv: {len(rows)}")
for i, r in enumerate(rows):
    print(f"[{i:3d}] id={r['id']:18s} cena={r['cena']:16s} b={r['bytes_jp']:2s} mx={r['max_bytes']:2s} | {r['original']}")

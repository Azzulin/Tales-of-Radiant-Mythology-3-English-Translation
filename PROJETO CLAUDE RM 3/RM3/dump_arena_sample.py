import csv

with open('lotes_p68/ARENA.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

print(f"Total rows in ARENA.tsv: {len(rows)}")
for i, r in enumerate(rows[:30]):
    print(f"[{i:3d}] id={r['id']:12s} b={r['bytes_jp']:2s} mx={r['max_bytes']:2s} | {r['original']}")

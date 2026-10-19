import csv

with open('lotes_p68/UI-01.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

print(f"Total rows in UI-01.tsv: {len(rows)}")
for i in range(0, len(rows), 20):
    for r in rows[i:i+4]:
        print(f"[{r['ordem']:3s}] b={r['bytes_jp']:2s} mx={r['max_bytes']:3s} | {r['original']}")

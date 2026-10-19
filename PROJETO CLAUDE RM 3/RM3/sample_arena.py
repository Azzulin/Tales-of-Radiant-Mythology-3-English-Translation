import csv

with open('lotes_p68/ARENA.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

for i in range(30, len(rows), 20):
    for r in rows[i:i+5]:
        print(f"[{r['ordem']:3s}] b={r['bytes_jp']:2s} mx={r['max_bytes']:3s} | {r['original']}")

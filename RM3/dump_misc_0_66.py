import csv

with open('lotes_p68/MISC.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

for i in range(67):
    r = rows[i]
    print(f"[{i:2d}] id={r['id']:18s} cena={r['cena']:16s} b={r['bytes_jp']:2s} mx={r['max_bytes']:2s} | {r['original']}")

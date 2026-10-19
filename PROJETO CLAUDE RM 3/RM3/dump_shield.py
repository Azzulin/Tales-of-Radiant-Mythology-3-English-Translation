import csv

with open('lotes_p68/SHIELD.tsv', encoding='utf-8') as f:
    shields = list(csv.DictReader(f, delimiter='\t'))

for i, r in enumerate(shields):
    print(f"{i:3d} | {r['id']:12s} | b={r['bytes_jp']:2s} | mx={r['max_bytes']:2s} | {r['original']}")

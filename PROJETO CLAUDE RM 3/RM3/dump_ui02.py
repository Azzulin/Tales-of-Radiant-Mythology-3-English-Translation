import csv

with open('lotes_p68/UI-02.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

with open('ui02_dump.txt', 'w', encoding='utf-8') as out:
    for i, r in enumerate(rows):
        out.write(f"[{i:3d}] id={r['id']:10s} b={r['bytes_jp']:2s} mx={r['max_bytes']:3s} | {r['original']}\n")
print(f"Dumped {len(rows)} lines to ui02_dump.txt")

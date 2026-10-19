import csv

with open('lotes_p68/SHIELD.tsv', encoding='utf-8') as f:
    shields = list(csv.DictReader(f, delimiter='\t'))

print("Analyzing structure:")
for i in range(16, len(shields)):
    r = shields[i]
    print(f"[{i:3d}] id={r['id']:11s} max={r['max_bytes']:2s} orig={r['original']}")

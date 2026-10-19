import csv, re

def norm(s):
    return re.sub(r'[\x13\x14\ufffd\x01-\x1f\s「」『』・、。/―…（）()]', '', s)

sin_rows = []
for n in ['01', '02', '03', '04']:
    with open(f'lotes_bancos/SINOPSE-{n}.tsv', encoding='utf-8') as f:
        sin_rows.extend(list(csv.DictReader(f, delimiter='\t')))

cap_rows = []
for n in ['01', '02', '03', '04']:
    with open(f'lotes_bancos/CAPITULO-{n}.tsv', encoding='utf-8') as f:
        cap_rows.extend(list(csv.DictReader(f, delimiter='\t')))

for i in range(52, len(sin_rows)):
    s = norm(sin_rows[i]['original'])
    c = norm(cap_rows[i]['original'])
    if s != c:
        print(f"Text diff at index {i}:")
        print(f"  SIN[{i}] ({sin_rows[i]['id']}): {repr(sin_rows[i]['original'])}")
        print(f"  CAP[{i}] ({cap_rows[i]['id']}): {repr(cap_rows[i]['original'])}")
        if i + 1 < len(cap_rows):
            print(f"  CAP[{i+1}] ({cap_rows[i+1]['id']}): {repr(cap_rows[i+1]['original'])}")
        break

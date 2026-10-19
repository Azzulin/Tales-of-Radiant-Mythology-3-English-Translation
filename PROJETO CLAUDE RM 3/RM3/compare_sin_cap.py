import csv, re

def strip_tags(s):
    return re.sub(r'[\x13\x14\ufffd\x01-\x1f]', '', s).replace(' ', '').replace('　', '')

sin_rows = []
for n in ['01', '02', '03', '04']:
    with open(f'lotes_bancos/SINOPSE-{n}.tsv', encoding='utf-8') as f:
        sin_rows.extend(list(csv.DictReader(f, delimiter='\t')))

cap_rows = []
for n in ['01', '02', '03', '04']:
    with open(f'lotes_bancos/CAPITULO-{n}.tsv', encoding='utf-8') as f:
        cap_rows.extend(list(csv.DictReader(f, delimiter='\t')))

print(f"Total SINOPSE: {len(sin_rows)}, Total CAPITULO: {len(cap_rows)}")

diffs = 0
matches = 0
for i in range(52, min(len(sin_rows), len(cap_rows))):
    s_orig = strip_tags(sin_rows[i]['original'])
    c_orig = strip_tags(cap_rows[i]['original'])
    if s_orig == c_orig:
        matches += 1
    else:
        diffs += 1
        if diffs <= 10:
            print(f"Diff at idx {i}:")
            print("  SIN:", repr(sin_rows[i]['original']))
            print("  CAP:", repr(cap_rows[i]['original']))

print(f"From idx 52 to {min(len(sin_rows), len(cap_rows))}: matches={matches}, diffs={diffs}")
if len(cap_rows) > len(sin_rows):
    print(f"Extra in CAPITULO: {cap_rows[-1]['id']}: {repr(cap_rows[-1]['original'])}")

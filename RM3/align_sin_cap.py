import csv, difflib, re

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

sin_texts = [norm(r['original']) for r in sin_rows[52:]]
cap_texts = [norm(r['original']) for r in cap_rows[52:]]

sm = difflib.SequenceMatcher(None, sin_texts, cap_texts)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag != 'equal':
        print(f"Opcode {tag}: SIN[{i1+52}:{i2+52}] vs CAP[{j1+52}:{j2+52}]")
        for idx in range(i1+52, i2+52):
            print(f"  SIN: {sin_rows[idx]['id']}: {repr(sin_rows[idx]['original'])}")
        for idx in range(j1+52, j2+52):
            print(f"  CAP: {cap_rows[idx]['id']}: {repr(cap_rows[idx]['original'])}")

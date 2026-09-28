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

print("Checking 52 to 421:")
mismatch_before = 0
for i in range(52, 422):
    s = norm(sin_rows[i]['original'])
    c = norm(cap_rows[i]['original'])
    if s != c:
        mismatch_before += 1
        print(f"Mismatch before at {i}: SIN={sin_rows[i]['id']} CAP={cap_rows[i]['id']}: {s} vs {c}")

print(f"Total mismatches before 422: {mismatch_before}")

print("\nChecking 424 to 1125 (cap_idx vs sin_idx = cap_idx - 1):")
mismatch_after = 0
for c_idx in range(424, 1126):
    s_idx = c_idx - 1
    s = norm(sin_rows[s_idx]['original'])
    c = norm(cap_rows[c_idx]['original'])
    if s != c:
        mismatch_after += 1
        if mismatch_after <= 10:
            print(f"Mismatch after at CAP[{c_idx}] vs SIN[{s_idx}]:")
            print("  CAP:", repr(cap_rows[c_idx]['original']))
            print("  SIN:", repr(sin_rows[s_idx]['original']))

print(f"Total mismatches after 424: {mismatch_after}")

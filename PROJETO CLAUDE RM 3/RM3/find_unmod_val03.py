import json
from build_val03_perfect import out, d

unmod = []
for i, x in enumerate(d['itens']):
    if x['id'] not in out:
        unmod.append((i, x['id'], x['en'], x['bytes'] - x['alvo_bytes']))

print(f"Unmodified in VAL-03: {len(unmod)}")
with open('unmod_val03.txt', 'w', encoding='utf-8') as f:
    for i, item_id, en, need in unmod:
        f.write(f"[{i:03d}] {item_id} (cut {need}) | {en}\n")

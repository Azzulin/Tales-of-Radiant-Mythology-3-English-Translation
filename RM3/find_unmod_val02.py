import json
from gen_val02 import build_val02

d = json.load(open('dados/item_equip_shrink/VAL-02.json', encoding='utf-8'))
out = build_val02()

unmod = []
for i, x in enumerate(d['itens']):
    if x['id'] not in out:
        unmod.append((i, x['id'], x['en'], x['bytes'] - x['alvo_bytes']))

print(f"Unmodified in VAL-02: {len(unmod)}")
with open('unmod_val02.txt', 'w', encoding='utf-8') as f:
    for i, item_id, en, need in unmod:
        f.write(f"[{i:03d}] {item_id} (cut {need}) | {en}\n")

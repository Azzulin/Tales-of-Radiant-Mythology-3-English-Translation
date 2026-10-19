import json
from gen_val01 import build_val01
from val_check import nomes_proprios

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']
out = build_val01()

needed_items = []
for i, x in enumerate(itens):
    item_id = x['id']
    old = x['en']
    need = x['bytes'] - x['alvo_bytes']
    if item_id in out:
        new = out[item_id]
        cut = len(old) - len(new)
        if cut < need:
            needed_items.append((i, item_id, old, new, cut, need))
    else:
        needed_items.append((i, item_id, old, None, 0, need))

print(f"Items needing more cut: {len(needed_items)} / {len(itens)}")
with open('val01_needs_cut.txt', 'w', encoding='utf-8') as f:
    for i, item_id, old, new, cut, need in needed_items:
        f.write(f"[{i:03d}] {item_id} | cut: {cut} / need: {need} (diff: {need-cut})\n")
        f.write(f"  OLD: {old}\n")
        if new:
            f.write(f"  CUR: {new}\n")
        f.write(f"  PROPS: {sorted(nomes_proprios(old))}\n\n")

print("Saved to val01_needs_cut.txt")

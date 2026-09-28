import json, re
from auto_shorten import make_rules, shorten_text
from val_check import nomes_proprios

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
rules = make_rules()

unmodified = []
for i, x in enumerate(d['itens']):
    en = x['en']
    s = shorten_text(en, rules)
    if s == en:
        unmodified.append((i, x['id'], x['bytes'] - x['alvo_bytes'], nomes_proprios(en), en))

print(f"Unmodified items: {len(unmodified)}")
with open('unmodified_val01.txt', 'w', encoding='utf-8') as f:
    for i, item_id, need, props, en in unmodified:
        f.write(f"[{i:03d}] {item_id} (cut {need}) | Props: {sorted(props)}\n  {en}\n")
print("Saved to unmodified_val01.txt")

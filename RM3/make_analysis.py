import json, re

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']

# Let's write an inspection file that lists all items with id, old, need cut, and proper nouns
with open('val01_analysis.txt', 'w', encoding='utf-8') as f:
    for i, x in enumerate(itens):
        f.write(f"[{i:03d}] {x['id']} | need cut: {x['bytes'] - x['alvo_bytes']}\n")
        f.write(f"  EN: {x['en']}\n")
        f.write(f"  JP: {x['jp']}\n\n")

print(f"Wrote {len(itens)} items to val01_analysis.txt")

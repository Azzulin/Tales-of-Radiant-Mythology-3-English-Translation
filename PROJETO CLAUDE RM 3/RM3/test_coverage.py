import json, re

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))

matched = 0
for x in d['itens']:
    t = x['en']
    if any(t.startswith(p) for p in [
        'An arcane arte', 'A secret arte', 'A skill that', 'An arte',
        'Weapon equipped', 'The recipe for', 'A key', 'Title given'
    ]):
        matched += 1

print(f"Matched {matched} of {len(d['itens'])} items with common prefixes.")

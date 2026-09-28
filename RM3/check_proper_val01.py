import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))

# Let's inspect all items that have proper nouns first
with_proper = []
without_proper = []
for x in d['itens']:
    np = nomes_proprios(x['en'])
    if np:
        with_proper.append((x['id'], np, x['en']))
    else:
        without_proper.append((x['id'], x['en']))

print(f"Items with proper nouns: {len(with_proper)}")
print(f"Items without proper nouns: {len(without_proper)}")
print("\nSample items with proper nouns:")
for item_id, np, text in with_proper[:15]:
    print(f"[{item_id}] Proper: {np}")
    print(f"  {text}")

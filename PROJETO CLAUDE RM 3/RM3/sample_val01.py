import json, re

# Let's inspect all items in VAL-01 by their JP text and current EN text
d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
items = d['itens']

print(f"Total items in VAL-01: {len(items)}")
# Print items with index to see their IDs and text
for idx, x in enumerate(items):
    cut = x['bytes'] - x['alvo_bytes']
    # print every 10th item
    if idx % 15 == 0:
        print(f"[{idx}] {x['id']} (len {x['bytes']} -> alvo {x['alvo_bytes']}, cut {cut}): {x['en']}")

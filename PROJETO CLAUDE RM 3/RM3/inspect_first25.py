import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
items = d['itens']

# Let's inspect the first 50 items and see their target reductions
for x in items[:25]:
    props = nomes_proprios(x['en'])
    cut_needed = x['bytes'] - x['alvo_bytes']
    print(f"[{x['id']}] need {cut_needed} B | Props: {props}")
    print("  OLD:", x['en'])

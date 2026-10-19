import json, re
from val_check import nomes_proprios, CAUDA, COMUM

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']

# Let's inspect each item and design clean shortenings
for i, x in enumerate(itens):
    en = x['en']
    item_id = x['id']
    props = nomes_proprios(en)
    need = x['bytes'] - x['alvo_bytes']
    # print first 30
    if i < 30:
        print(f"{i:03d} | {item_id} (cut {need}) | Props: {sorted(props)}")
        print(f"  OLD: {en}")

import json
from val_check import nomes_proprios

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
for idx in range(0, 50):
    x = d['itens'][idx]
    props = nomes_proprios(x['en'])
    cut = x['bytes'] - x['alvo_bytes']
    print(f"[{x['id']}] cut {cut} | Props: {props}")
    print("  OLD:", x['en'])

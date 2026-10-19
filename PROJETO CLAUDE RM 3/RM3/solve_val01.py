import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
items = d['itens']

# Let's inspect the distribution of cut needed
cuts = [x['bytes'] - x['alvo_bytes'] for x in items]
print(f"VAL-01: {len(items)} items. Total cut needed: {sum(cuts)} B. Target meta: {d['meta_bytes_a_cortar']} B.")
print(f"Min cut: {min(cuts)}, Max cut: {max(cuts)}, Avg: {sum(cuts)/len(cuts):.2f}")

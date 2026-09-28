import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']

# Let's inspect all items in blocks of 50
print(f"Total items: {len(itens)}")

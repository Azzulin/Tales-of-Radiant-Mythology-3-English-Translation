import json, re
from val_check import validate_dict, nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
items = d['itens']

# Let's inspect all 277 items in VAL-01 in groups to craft concise equivalents.
print("Loaded VAL-01 items:", len(items))

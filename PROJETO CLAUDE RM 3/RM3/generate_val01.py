import json, re
from val_check import validate_dict, nomes_proprios, CAUDA

# Load input
in_path = 'dados/item_equip_shrink/VAL-01.json'
out_path = 'dados/item_equip_shrink/VAL-01_out.json'
d = json.load(open(in_path, encoding='utf-8'))
items = {x['id']: x for x in d['itens']}

# We will define precise shortenings for each of the 277 items.
# Let's inspect and create the map.
# To make it clean and maintainable, we can define a base dictionary of shortenings.

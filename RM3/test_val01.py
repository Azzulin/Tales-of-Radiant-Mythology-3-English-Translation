import json, re
from val_check import validate_dict, nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))

print("Total items:", len(d['itens']))
print("Meta bytes to cut:", d['meta_bytes_a_cortar'])

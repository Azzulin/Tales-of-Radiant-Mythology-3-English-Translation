import json, re

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))

with open('val01_data.py', 'w', encoding='utf-8') as f:
    f.write("# Shortened descriptions for VAL-01\n\nVAL01_MAP = {\n")
    for x in d['itens']:
        f.write(f"    # {x['id']} | JP: {x['jp']}\n")
        f.write(f"    # OLD: {x['en']} (len {len(x['en'])}, need cut {x['bytes'] - x['alvo_bytes']})\n")
        f.write(f"    {repr(x['id'])}: {repr(x['en'])},\n\n")
    f.write("}\n")

print("Generated val01_data.py template")

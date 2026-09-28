import json

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
for x in d['itens'][:30]:
    print(f"[{x['id']}] ({x['bytes']} -> {x['alvo_bytes']} B, need cut {x['bytes'] - x['alvo_bytes']})")
    print("  JP:", x['jp'])
    print("  EN:", x['en'])

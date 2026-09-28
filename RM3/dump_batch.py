import json, sys

batch = sys.argv[1] if len(sys.argv) > 1 else 'VAL-01'
d = json.load(open(f'dados/item_equip_shrink/{batch}.json', encoding='utf-8'))
with open(f'scratch_{batch}.txt', 'w', encoding='utf-8') as f:
    for i, x in enumerate(d['itens']):
        need = x['bytes'] - x['alvo_bytes']
        f.write(f"{i:03d} | {x['id']} | {x['bytes']} -> {x['alvo_bytes']} (cut {need}) | {x['en']}\n")
print(f"Dumped {len(d['itens'])} items to scratch_{batch}.txt")

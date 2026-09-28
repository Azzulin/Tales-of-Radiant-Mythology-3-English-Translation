import json

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))

with open('scratch_val01_all.txt', 'w', encoding='utf-8') as out:
    for x in d['itens']:
        out.write(f"ID: {x['id']} | BYTES: {x['bytes']} -> {x['alvo_bytes']} (CUT: {x['bytes']-x['alvo_bytes']})\n")
        out.write(f"JP: {x['jp']}\n")
        out.write(f"EN: {x['en']}\n\n")

print(f"Wrote {len(d['itens'])} items to scratch_val01_all.txt")

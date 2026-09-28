import json, sys

batch = sys.argv[1] if len(sys.argv) > 1 else 'VAL-01'
d = json.load(open(f'dados/item_equip_shrink/{batch}.json', encoding='utf-8'))

non_standard = []
for i, x in enumerate(d['itens']):
    en = x['en']
    if not (en.startswith('Arcane arte:') or en.startswith('Secret arte:') or en.startswith('Arte:') or en.startswith('A skill that')):
        non_standard.append((i, x['id'], x['bytes'], x['alvo_bytes'], en))

print(f"Total non-standard items in {batch}: {len(non_standard)} / {len(d['itens'])}")
for i, item_id, b, alvo, en in non_standard:
    print(f"{i:03d} | {item_id} | {b}->{alvo} (cut {b-alvo}) | {en}")

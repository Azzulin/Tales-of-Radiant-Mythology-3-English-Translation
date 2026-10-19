import sys, json

batch = sys.argv[1] if len(sys.argv) > 1 else 'VAL3-01'
d = json.load(open(f'lotes_corte3/{batch}.json', encoding='utf-8'))
print(f"=== {batch} ===")
print("Meta:", d['meta_bytes_a_cortar'], "Total itens:", len(d['itens']))
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
count = int(sys.argv[3]) if len(sys.argv) > 3 else 30
for i in range(start, min(start + count, len(d['itens']))):
    x = d['itens'][i]
    print(f"[{i:03d}] {x['id']} | {x['en']}")

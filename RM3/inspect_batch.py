import json, re, sys, os
from val_check import nomes_proprios, CAUDA, COMUM

def inspect_batch(batch_name):
    path = f'dados/item_equip_shrink/{batch_name}.json'
    d = json.load(open(path, encoding='utf-8'))
    itens = d['itens']
    meta = d['meta_bytes_a_cortar']
    print(f"=== {batch_name} ({len(itens)} itens, meta {meta} B) ===")
    
    with_proper = []
    for x in itens:
        props = nomes_proprios(x['en'])
        if props:
            with_proper.append((x['id'], props, x['en']))
            
    print(f"Items with proper nouns: {len(with_proper)} / {len(itens)}")
    for item_id, props, en in with_proper:
        print(f"  {item_id}: {sorted(props)} | {en}")
    return itens

if __name__ == '__main__':
    batch = sys.argv[1] if len(sys.argv) > 1 else 'VAL-01'
    inspect_batch(batch)

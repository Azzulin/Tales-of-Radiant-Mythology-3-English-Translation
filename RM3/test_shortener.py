import json, re, sys
from val_check import validate_dict, nomes_proprios, CAUDA

def run(batch_name):
    path = f'dados/item_equip_shrink/{batch_name}.json'
    d = json.load(open(path, encoding='utf-8'))
    itens = d['itens']
    
    out = {}
    for x in itens:
        en = x['en']
        item_id = x['id']
        need = x['bytes'] - x['alvo_bytes']
        
        # Test basic transformations
        # ...
    return out

if __name__ == '__main__':
    run('VAL-01')

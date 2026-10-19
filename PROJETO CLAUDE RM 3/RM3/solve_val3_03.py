import json, re
from ferramentas.val_valida_retorno import valida, nomes_proprios, CAUDA, COMUM

d = json.load(open('lotes_corte3/VAL3-03.json', encoding='utf-8'))
itens = d['itens']
meta = d['meta_bytes_a_cortar']

print(f"VAL3-03: {len(itens)} itens, meta: {meta}")

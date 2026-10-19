import json
from test_more_trims import out

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
orig = {x['id']: x for x in d['itens']}

under_target = []
for k, v in out.items():
    x = orig[k]
    cut = len(x['en']) - len(v)
    need = x['bytes'] - x['alvo_bytes']
    if cut < need:
        under_target.append((k, cut, need, need - cut, v, x['en']))

under_target.sort(key=lambda t: t[3], reverse=True)
print(f"Items under individual target: {len(under_target)}")
for k, cut, need, diff, v, old in under_target[:20]:
    print(f"{k} | cut: {cut} / need: {need} (need {diff} more)")
    print(f"  OLD: {old}")
    print(f"  NEW: {v}")

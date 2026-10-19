import json, re

for n in ['01', '02', '03', '04']:
    fn = f'dados/item_equip_shrink/VAL-{n}.json'
    d = json.load(open(fn, encoding='utf-8'))
    print(f"\n--- VAL-{n} ---")
    prefixes = {}
    for x in d['itens']:
        m = re.match(r'^([A-Z][a-z]+(?:\s+[a-z]+){0,3}:?)\s+', x['en'])
        if m:
            p = m.group(1)
            prefixes[p] = prefixes.get(p, 0) + 1
    for p, c in sorted(prefixes.items(), key=lambda t: t[1], reverse=True)[:10]:
        print(f"  {repr(p)}: {c}")

import glob, csv

found = 0
for p in sorted(glob.glob('lotes/*_retorno.tsv')):
    rows = list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    for r in rows:
        orig = r.get('original', '')
        if '\x13' in orig:
            print(f"File: {p}, ID: {r['id']}")
            print(f"  Orig: {repr(orig)}")
            print(f"  Trad: {repr(r.get('traducao', ''))}")
            found += 1
            if found >= 5:
                break
    if found >= 5:
        break

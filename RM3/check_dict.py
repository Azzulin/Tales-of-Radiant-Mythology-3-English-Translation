import re, csv

CAUDA = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with',
         'from', 'and', 'or', 'but', 'that', 'which', 'who', 'whose', 'as',
         'is', 'are', 'was', 'were', 'be', 'been', 'its', 'this', 'these',
         'those', 'into', 'onto', 'over', 'under', 'than', 'then', 'when',
         'while', 'has', 'have', 'had', 'will', 'said', 'made', 'used',
         'very', 'more', 'most', 'such', 'so', 'his', 'her', 'their'}

def check_dict(d, orig_file):
    with open(orig_file, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    
    soma = 0
    teto = sum(int(r['max_bytes']) + 1 for r in rows)
    errors = []
    
    for r in rows:
        rid = r['id']
        t = d.get(rid, '').strip()
        mx = int(r['max_bytes']) if r.get('max_bytes') else 0
        soma += len(t.encode('ascii', errors='replace')) + 1
        
        jp_marc = r['original'].count(chr(9675)*2)
        if jp_marc and (t.count('OO') + t.count(chr(9675)*2)) < jp_marc:
            errors.append((rid, f"Missing OO marker (orig has {jp_marc})"))
            
        jp = r['original']
        jp_pontuado = jp.rstrip()[-1:] in '。！？.!?'
        if len(t) > 25 and ' ' in t:
            if jp_pontuado and t.rstrip()[-1:] not in '.!?)':
                errors.append((rid, f"Must end with punctuation (.!?)): {t[-20:]!r}"))
            pal = re.findall(r"[A-Za-z']+", t)
            if pal and pal[-1].lower() in CAUDA:
                errors.append((rid, f"Ending with CAUDA word '{pal[-1]}': {t[-20:]!r}"))
                
    print(f"Total bytes: {soma} / Budget: {teto} (Diff: {teto - soma})")
    print(f"Errors count: {len(errors)}")
    for e in errors[:15]:
        print(" ", e)
    return len(errors) == 0 and soma <= teto

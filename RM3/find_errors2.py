from sinopse_dict2 import SINOPSE_2
import re, csv

CAUDA = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with',
         'from', 'and', 'or', 'but', 'that', 'which', 'who', 'whose', 'as',
         'is', 'are', 'was', 'were', 'be', 'been', 'its', 'this', 'these',
         'those', 'into', 'onto', 'over', 'under', 'than', 'then', 'when',
         'while', 'has', 'have', 'had', 'will', 'said', 'made', 'used',
         'very', 'more', 'most', 'such', 'so', 'his', 'her', 'their'}

with open('lotes_bancos/SINOPSE-02.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

for r in rows:
    rid = r['id']
    t = SINOPSE_2.get(rid, '').strip()
    jp_marc = r['original'].count(chr(9675)*2)
    if jp_marc and (t.count('OO') + t.count(chr(9675)*2)) < jp_marc:
        print(rid, 'MISSING OO:', repr(t), 'ORIG:', repr(r['original']))
    jp = r['original']
    jp_pontuado = jp.rstrip()[-1:] in '。！？.!?'
    if len(t) > 25 and ' ' in t:
        if jp_pontuado and t.rstrip()[-1:] not in '.!?)':
            print(rid, 'NOT PONTUADO:', repr(t))
        pal = re.findall(r"[A-Za-z']+", t)
        if pal and pal[-1].lower() in CAUDA:
            print(rid, 'CAUDA:', pal[-1], repr(t))

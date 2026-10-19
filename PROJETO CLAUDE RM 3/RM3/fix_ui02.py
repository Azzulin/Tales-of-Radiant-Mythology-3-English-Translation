import csv

with open('lotes_p68/UI-02.tsv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    fieldnames = reader.fieldnames
    rows = list(reader)

from build_ui02 import T

T['ui#510'] = ('Add Poison', '毒付与 (max 13)')
T['ui#602'] = ('Taking this item allows', '')
T['ui#603'] = ('restarting the story,', '')
T['ui#604'] = ('while keeping your level.', '')

for r in rows:
    rid = r['id']
    tr, nt = T[rid]
    r['traducao'] = tr
    if nt:
        r['nota_do_tradutor'] = nt

out_p = 'lotes_p68/UI-02_retorno.tsv'
with open(out_p, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    w.writeheader()
    w.writerows(rows)
print("Updated UI-02_retorno.tsv")

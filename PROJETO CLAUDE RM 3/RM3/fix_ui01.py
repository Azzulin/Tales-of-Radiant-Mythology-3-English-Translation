import csv

# Read original
with open('lotes_p68/UI-01.tsv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    fieldnames = reader.fieldnames
    rows = list(reader)

from build_ui01 import T

# Fix the specific keys
T['ui#46'] = ('Select your new class.', '')
T['ui#148'] = ('If you quit now,', '')
T['ui#149'] = ('unsaved progress is lost.', '')
T['ui#150'] = ('Are you sure?', '')
T['ui#170'] = ('*Material', '')
T['ui#180'] = ('Choose the base equipment.', '')
T['ui#184'] = ('From material equipment:', '')
T['ui#185'] = ('Select skill to synthesize.', '')
T['ui#190'] = ('No upgrade slots remaining.', '')
T['ui#201'] = ('Gald needed for synthesis.', '')
T['ui#202'] = ('*Material equipment', '')
T['ui#203'] = ('will be lost forever!', '')

for r in rows:
    rid = r['id']
    tr, nt = T[rid]
    r['traducao'] = tr
    if nt:
        r['nota_do_tradutor'] = nt

out_p = 'lotes_p68/UI-01_retorno.tsv'
with open(out_p, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    w.writeheader()
    w.writerows(rows)
print("Updated UI-01_retorno.tsv")

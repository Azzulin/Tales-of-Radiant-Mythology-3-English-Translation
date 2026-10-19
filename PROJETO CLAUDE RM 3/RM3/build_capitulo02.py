import csv
from capitulo_dict2 import CAPITULO_2

in_path = 'lotes_bancos/CAPITULO-02.tsv'
out_path = 'lotes_bancos/CAPITULO-02_retorno.tsv'

with open(in_path, encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

fieldnames = list(rows[0].keys())

for r in rows:
    row_id = r['id']
    if row_id in CAPITULO_2:
        r['traducao'] = CAPITULO_2[row_id]
        if not r['nota_do_tradutor']:
            r['nota_do_tradutor'] = 'Chapter story narrative translation.'
    else:
        print(f"Missing translation for {row_id}")

with open(out_path, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {out_path}")

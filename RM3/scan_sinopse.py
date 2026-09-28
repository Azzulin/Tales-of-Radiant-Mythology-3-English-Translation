import csv

all_rows = []
for num in ['01', '02', '03', '04']:
    with open(f'lotes_bancos/SINOPSE-{num}.tsv', encoding='utf-8') as f:
        all_rows.extend(list(csv.DictReader(f, delimiter='\t')))

print('Total rows:', len(all_rows))
print('Rows with あらすじ:')
for i, r in enumerate(all_rows):
    if 'あらすじ' in r['original']:
        print(f"  idx={i} {r['id']}: {r['original']}")

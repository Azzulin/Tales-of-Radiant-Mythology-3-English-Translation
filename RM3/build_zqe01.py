import csv

with open('lotes_p68/ZQE-01.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

translations = {
    'zqe_judas#0': 'Blood rejects blood.',
    'zqe_judas#1': 'Heart breaks heart.',
    'zqe_judas#2': 'Miracles never come.',
    'zqe_judas#3': 'Dreams...',
    'zqe_judas#4': 'They do not exist there.',
    'zqe_judas#5': 'Will you resist?!'
}

for r in rows:
    r['traducao'] = translations[r['id']]
    r['nota_do_tradutor'] = 'Judas Majin Rengokusatsu chant (Destiny 2 standard).'

fieldnames = list(rows[0].keys())

with open('lotes_p68/ZQE-01_retorno.tsv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    writer.writeheader()
    writer.writerows(rows)

print("Wrote lotes_p68/ZQE-01_retorno.tsv")

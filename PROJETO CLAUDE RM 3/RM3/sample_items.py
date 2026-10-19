import glob, csv

for p in glob.glob('lotes/ITEM-*_retorno.tsv')[:5]:
    with open(p, encoding='utf-8') as f:
        reader = list(csv.DictReader(f, delimiter='\t'))
        for r in reader[:15]:
            print(f"{r['id']} | orig={r['original']} | trans={r['traducao']}")

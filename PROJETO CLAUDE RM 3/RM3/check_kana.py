import glob, csv

for p in glob.glob('lotes/ITEM-*_retorno.tsv'):
    with open(p, encoding='utf-8') as f:
        reader = list(csv.DictReader(f, delimiter='\t'))
        for r in reader:
            if 'ノタテ' in r['original'] or 'ナベノフタ' in r['original']:
                print(p, r['original'], '->', r['traducao'])

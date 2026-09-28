import glob, csv

for p in glob.glob('lotes/*_retorno.tsv'):
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if 'チョコ' in r['original'] or 'どん' in r['original'] or 'かつ' in r['original'] or 'ヒラメ' in r['original']:
                print(p, r['original'], '->', r.get('traducao'))

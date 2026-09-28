import glob, csv

glossary = {}
for p in glob.glob('lotes/*_retorno.tsv') + ['lotes_p68/CAMPO-02_retorno.tsv', 'lotes_p68/SHIELD_retorno.tsv', 'lotes_p68/MISC_retorno.tsv', 'lotes_p68/ARENA_retorno.tsv']:
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            orig = r.get('original', '').strip()
            tr = r.get('traducao', '').strip()
            if orig and tr and orig not in glossary:
                glossary[orig] = tr

print(f"Total glossary terms: {len(glossary)}")

for uifile in ['UI-01.tsv', 'UI-02.tsv', 'UI-03.tsv']:
    with open(f'lotes_p68/{uifile}', encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    matched = [r for r in rows if r['original'].strip() in glossary]
    print(f"{uifile}: {len(matched)} / {len(rows)} matched directly in glossary")

import glob, csv

all_trans = {}
for p in glob.glob('lotes/*_retorno.tsv'):
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            orig = r.get('original', '').strip()
            tr = r.get('traducao', '').strip()
            if orig and tr and orig not in all_trans:
                all_trans[orig] = tr

with open('lotes_p68/SKIT-01.tsv', encoding='utf-8') as f:
    s1 = list(csv.DictReader(f, delimiter='\t'))
with open('lotes_p68/SKIT-02.tsv', encoding='utf-8') as f:
    s2 = list(csv.DictReader(f, delimiter='\t'))

m1 = [r for r in s1 if r['original'] in all_trans]
m2 = [r for r in s2 if r['original'] in all_trans]
print(f"SKIT-01 matches: {len(m1)} / {len(s1)}")
print(f"SKIT-02 matches: {len(m2)} / {len(s2)}")

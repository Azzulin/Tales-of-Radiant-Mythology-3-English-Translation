import csv

with open('lotes_p68/SKIT-01.tsv', encoding='utf-8') as f:
    s1 = list(csv.DictReader(f, delimiter='\t'))

with open('lotes_p68/SKIT-02.tsv', encoding='utf-8') as f:
    s2 = list(csv.DictReader(f, delimiter='\t'))

print(f"SKIT-01 lines: {len(s1)}")
print(f"SKIT-02 lines: {len(s2)}")

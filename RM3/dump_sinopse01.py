import csv

with open('lotes_bancos/SINOPSE-01.tsv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f, delimiter='\t'))

with open('scratch_sinopse01_dump.txt', 'w', encoding='utf-8') as out:
    for r in rows:
        out.write(f"{r['id']}\t{r['bytes_jp']}\t{r['max_bytes']}\t{r['original']}\n")

print("Dumped SINOPSE-01 to scratch_sinopse01_dump.txt")

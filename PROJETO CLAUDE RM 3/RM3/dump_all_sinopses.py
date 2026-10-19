import csv

for num in ['01', '02', '03', '04']:
    in_fn = f'lotes_bancos/SINOPSE-{num}.tsv'
    out_fn = f'scratch_sinopse_{num}_raw.txt'
    with open(in_fn, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    with open(out_fn, 'w', encoding='utf-8') as out:
        for r in rows:
            out.write(f"{r['id']}\t{r['bytes_jp']}\t{r['max_bytes']}\t{r['original']}\n")
    print(f"Dumped {len(rows)} lines to {out_fn}")

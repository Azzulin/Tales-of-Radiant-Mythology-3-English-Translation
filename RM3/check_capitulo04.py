from sinopse_dict3 import SINOPSE_3
from sinopse_dict4 import SINOPSE_4
from check_dict import check_dict

CAPITULO_4 = {}

# capitulo#960 is sinopse#959
CAPITULO_4['capitulo#960'] = SINOPSE_3['sinopse#959']

# capitulo#961 to #1125 map to sinopse#(i-1) in SINOPSE_4
for i in range(961, 1126):
    CAPITULO_4[f'capitulo#{i}'] = SINOPSE_4[f'sinopse#{i-1}']

print(f"Total entries in CAPITULO_4: {len(CAPITULO_4)}")
check_dict(CAPITULO_4, 'lotes_bancos/CAPITULO-04.tsv')

with open('capitulo_dict4.py', 'w', encoding='utf-8') as f:
    f.write("CAPITULO_4 = {\n")
    for k in sorted(CAPITULO_4.keys(), key=lambda x: int(x.split('#')[1])):
        f.write(f"    {repr(k)}: {repr(CAPITULO_4[k])},\n")
    f.write("}\n")

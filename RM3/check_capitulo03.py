from sinopse_dict2 import SINOPSE_2
from sinopse_dict3 import SINOPSE_3
from check_dict import check_dict

CAPITULO_3 = {}

# capitulo#640 is sinopse#639
CAPITULO_3['capitulo#640'] = SINOPSE_2['sinopse#639']

# capitulo#641 to #959 map to sinopse#(i-1) in SINOPSE_3
for i in range(641, 960):
    CAPITULO_3[f'capitulo#{i}'] = SINOPSE_3[f'sinopse#{i-1}']

print(f"Total entries in CAPITULO_3: {len(CAPITULO_3)}")
check_dict(CAPITULO_3, 'lotes_bancos/CAPITULO-03.tsv')

with open('capitulo_dict3.py', 'w', encoding='utf-8') as f:
    f.write("CAPITULO_3 = {\n")
    for k in sorted(CAPITULO_3.keys(), key=lambda x: int(x.split('#')[1])):
        f.write(f"    {repr(k)}: {repr(CAPITULO_3[k])},\n")
    f.write("}\n")

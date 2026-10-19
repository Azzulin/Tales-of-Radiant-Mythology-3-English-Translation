from sinopse_dict2 import SINOPSE_2
from check_dict import check_dict

CAPITULO_2 = {}

# 320 to 421
for i in range(320, 422):
    CAPITULO_2[f'capitulo#{i}'] = SINOPSE_2[f'sinopse#{i}']

# 422 and 423
CAPITULO_2['capitulo#422'] = 'To prevent further civilian contact...'
CAPITULO_2['capitulo#423'] = 'OO led Tytree and Meredy,'

# 424 to 639 map to sinopse#(i-1)
for i in range(424, 640):
    CAPITULO_2[f'capitulo#{i}'] = SINOPSE_2[f'sinopse#{i-1}']

print(f"Total entries in CAPITULO_2: {len(CAPITULO_2)}")
check_dict(CAPITULO_2, 'lotes_bancos/CAPITULO-02.tsv')

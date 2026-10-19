from sinopse_dict3 import SINOPSE_3
from check_dict import check_dict

FIXES = {
    'sinopse#645': 'Furthermore, Lazaris and her realm, Zirdia,',
    'sinopse#646': 'were sealed within a dimensional prison',
    'sinopse#652': 'via Soul Alchemy, requiring retrieval',
    'sinopse#653': 'of the rare Salt Crystal.',
    'sinopse#658': 'Suddenly, a brute blocked OO and friends,',
    'sinopse#659': 'barring their forward path.',
    'sinopse#660': 'It was Barbatos, infamous as a warrior',
    'sinopse#661': 'who attacked any strong opponent.',
    'sinopse#666': "Through OO's strength, they drove Barbatos",
    'sinopse#667': 'away, leaving reckless Kyle',
    'sinopse#671': 'The remaining two sealing items were found.',
    'sinopse#686': "to understand the Tree's true intent.",
    'sinopse#689': 'Landscapes and Documents seen by Kanonno alone.',
    'sinopse#812': 'En route, a faint cry carried on the wind.',
    'sinopse#819': 'Saleh attacked with immense confidence,',
    'sinopse#820': "yet fell before OO's guild allies.",
    'sinopse#876': 'they shrank back toward Lazaris in fear.',
    'sinopse#878': 'Despairing of Luminasia, those souls',
    'sinopse#879': 'chose mutation willingly.',
    'sinopse#906': 'OO and companions sought the true motive.',
    'sinopse#907': 'Kanonno learned from Rocks that she painted',
    'sinopse#908': 'her parents without knowing.',
    'sinopse#909': 'To uncover memories hidden within herself,',
    'sinopse#910': 'Kanonno asked to deploy her Document.',
    'sinopse#911': 'Yet detailed deployment carried grave risk.',
    'sinopse#925': 'they encountered Original Kanonno, embodiment',
    'sinopse#926': 'of the primeval World Tree itself.',
    'sinopse#927': 'Original Kanonno revealed that Luminasia,',
    'sinopse#928': 'and Zirdia were siblings of shared root.',
    'sinopse#932': 'Star Crystals acted both as a firm seal,',
    'sinopse#933': 'and a nurturing cradle for Zirdia.',
    'sinopse#945': "The food's Document integrated inside",
    'sinopse#946': 'those partaking of nourishment.',
    'sinopse#948': 'This proved a profound realization.',
}

SINOPSE_3.update(FIXES)

with open('sinopse_dict3.py', 'w', encoding='utf-8') as f:
    f.write("# Translation dictionary for SINOPSE-03 (ids 640 to 959)\n\nSINOPSE_3 = {\n")
    for k in sorted(SINOPSE_3.keys(), key=lambda x: int(x.split('#')[1])):
        f.write(f"    {repr(k)}: {repr(SINOPSE_3[k])},\n")
    f.write("}\n")

print("Updated sinopse_dict3.py, now running check_dict:")
check_dict(SINOPSE_3, 'lotes_bancos/SINOPSE-03.tsv')

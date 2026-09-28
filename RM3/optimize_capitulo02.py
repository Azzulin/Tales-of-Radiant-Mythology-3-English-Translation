from check_capitulo02 import CAPITULO_2
from check_dict import check_dict

# Trim ~250 bytes by making minor concise adjustments:
TRIMS = {
    'capitulo#320': 'Fearing relapse, they expected', # -9
    'capitulo#324': 'Unable to return, Joan and Miguel', # -5
    'capitulo#325': 'joined building Olta Village.', # -4
    'capitulo#328': 'Proving that red smoke was indeed', # -2
    'capitulo#332': 'Civilian contact had to cease,', # -8
    'capitulo#333': 'yet its next emergence was unknown.', # -8
    'capitulo#334': 'Expecting more requests, Ange', # -7
    'capitulo#339': 'an artifact opening sealed paths.', # -6
    'capitulo#340': 'Mint gave it to Ange with a quest.', # -6
    'capitulo#342': 'To awaken it, natural energy', # -10
    'capitulo#344': 'Infusion sites were Ring Spots,', # -10
    'capitulo#346': 'At Altata Volcano, OO', # -18
    'capitulo#347': 'infused the ring with primal energy,', # -4
    'capitulo#348': 'activating its power.', # -12
    'capitulo#350': 'greater power through infusions.', # -8
    'capitulo#354': 'granting authority to wield it.', # -8
    'capitulo#355': 'Intel on red smoke', # -18
    'capitulo#362': 'submitting a quest.', # -7
    'capitulo#366': 'To seek info on the smoke,', # -9
    'capitulo#373': 'Servants of the Dawn.', # -16
    'capitulo#374': 'Amidst war, new cults awaiting', # -4
    'capitulo#378': 'OO felt great frustration', # -12
    'capitulo#381': 'Rushing over, a beast rampaged.', # -12
    'capitulo#386': 'with the art of Light Qi.', # -12
    'capitulo#388': 'yet mining drove them away.', # -10
    'capitulo#408': 'was a branch of Soul Alchemy,', # -11
    'capitulo#410': 'Soul Alchemy alters blueprints', # -7
    'capitulo#416': 'An escort quest reached the guild', # -9
    'capitulo#420': 'Ange declined, deploying', # -10
    'capitulo#421': 'members to Rhubarb directly.', # -13
    'capitulo#433': 'Servants of the Dawn appeared.', # -10
    'capitulo#448': 'Red smoke reacted to wishes.', # -10
    'capitulo#467': 'at Almanac Ruins.', # -12
    'capitulo#470': 'They had to act quickly', # -11
    'capitulo#492': 'The entity was no Descender.', # -7
    'capitulo#516': 'Next destination: Mt. Absoule.', # -5
    'capitulo#548': 'The witness was not mortal.', # -16
}

CAPITULO_2.update(TRIMS)

print("Running check_dict on trimmed CAPITULO_2:")
check_dict(CAPITULO_2, 'lotes_bancos/CAPITULO-02.tsv')

with open('capitulo_dict2.py', 'w', encoding='utf-8') as f:
    f.write("CAPITULO_2 = {\n")
    for k in sorted(CAPITULO_2.keys(), key=lambda x: int(x.split('#')[1])):
        f.write(f"    {repr(k)}: {repr(CAPITULO_2[k])},\n")
    f.write("}\n")

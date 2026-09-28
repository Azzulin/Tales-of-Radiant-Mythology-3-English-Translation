import json, re
from ferramentas.val_valida_retorno import valida, nomes_proprios, CAUDA, COMUM

d = json.load(open('lotes_corte3/ARENA3.json', encoding='utf-8'))
itens = d['itens']
meta = d['meta_bytes_a_cortar']

overrides = {
    # 00: arena#71 (68B) NP: []
    'arena#71': 'Inseparable quartet joins the ring!', # 35B (cut 33)

    # 01: arena#67 (67B) NP: ['Best']
    'arena#67': 'Best rivals enter the ultimate match!', # 37B (cut 30)

    # 02: arena#172 (67B) NP: ['Even']
    'arena#172': 'Even unknighted, chivalry burns!', # 32B (cut 35)

    # 03: arena#201 (67B) NP: []
    'arena#201': 'Who dare challenge this quartet?', # 32B (cut 35)

    # 04: arena#237 (67B) NP: ['Gekogeko']
    'arena#237': 'Gekogeko assembled! Who dare challenge?', # 39B (cut 28)

    # 05: arena#58 (66B) NP: ['They']
    'arena#58': 'They bicker, but unite in the ring!', # 35B (cut 31)

    # 06: arena#69 (66B) NP: ['Fighting', 'They']
    'arena#69': 'Fighting like cats and dogs, They join!', # 39B (cut 27)

    # 07: arena#166 (65B) NP: ['They']
    'arena#166': 'They seem timid, yet fight fiercely!', # 36B (cut 29)

    # 08: arena#168 (65B) NP: ['Different']
    'arena#168': 'Different paths, both aid the weak!', # 35B (cut 30)

    # 09: arena#178 (65B) NP: ['Ad', 'Gen', 'Libitum', 'Poke']
    'arena#178': 'Poke-Gen: Ad Libitum squad arrives!', # 35B (cut 30)

    # 10: arena#205 (65B) NP: ['All', 'Win']
    'arena#205': 'All pervert kings gather! Win to join?', # 38B (cut 27)

    # 11: arena#140 (64B) NP: ['They']
    'arena#140': 'They clash, yet click in battle!', # 32B (cut 32)

    # 12: arena#142 (64B) NP: ['Sharp', 'They']
    'arena#142': 'Sharp tongues, yet They fit together!', # 37B (cut 27)

    # 13: arena#176 (64B) NP: ['Ad', 'Gen', 'Libitum', 'Neo']
    'arena#176': 'Neo-Gen: Ad Libitum squad arrives!', # 34B (cut 30)

    # 14: arena#194 (64B) NP: []
    'arena#194': 'Three clergy clash in evangelical fervor!', # 41B (cut 23)

    # 15: arena#56 (63B) NP: []
    'arena#56': 'Rich boy and stoic beauty join forces!', # 38B (cut 25)

    # 16: arena#128 (63B) NP: ['Brother']
    'arena#128': 'Brother and sister challenge you!', # 33B (cut 30)

    # 17: arena#196 (63B) NP: ['Three', 'True']
    'arena#196': 'True power in silence! Three throw down!', # 40B (cut 23)

    # 18: arena#152 (62B) NP: ['Crashing']
    'arena#152': 'Crashing in to protect his sister!', # 34B (cut 28)

    # 19: arena#187 (62B) NP: ['We']
    'arena#187': "We won't lose! The sisters enter!", # 33B (cut 29)

    # 20: arena#203 (62B) NP: ['Ad', 'Gen', 'Libitum', 'Seca']
    'arena#203': 'Seca-Gen: Ad Libitum team enters!', # 33B (cut 29)

    # 21: arena#88 (61B) NP: ['Always']
    'arena#88': 'Always lively, quartet gets serious!', # 36B (cut 25)

    # 22: arena#170 (61B) NP: ['Brawler', 'Slender']
    'arena#170': 'Slender punch power! Brawler girls join!', # 40B (cut 21)

    # 23: arena#189 (61B) NP: ['Somewhat']
    'arena#189': 'Somewhat eerie trio steps up to fight!', # 38B (cut 23)

    # 24: arena#111 (60B) NP: ['Two']
    'arena#111': 'Two sheriff-like officers enter!', # 32B (cut 28)

    # 25: arena#198 (60B) NP: ['Chivalric', 'Smash']
    'arena#198': 'Smash evil! Chivalric trio enters!', # 34B (cut 26)

    # 26: arena#61 (59B) NP: []
    'arena#61': 'Date at colosseum? A couple enters!', # 35B (cut 24)

    # 27: arena#73 (59B) NP: ['Polar']
    'arena#73': 'Polar opposites enter the fray!', # 31B (cut 28)

    # 28: arena#157 (59B) NP: ['Searching']
    'arena#157': 'Searching for true strength, trio joins!', # 40B (cut 19)

    # 29: arena#185 (59B) NP: ['Sometimes']
    'arena#185': 'Sometimes bold, three spearmen enter!', # 37B (cut 22)

    # 30: arena#6 (58B) NP: ['Three']
    'arena#6': 'Three challengers call out! Face them?', # 38B (cut 20)

    # 31: arena#42 (58B) NP: []
    'arena#42': 'Classic hero and heroine team enters!', # 37B (cut 21)

    # 32: arena#8 (57B) NP: ['Four']
    'arena#8': 'Four challengers call out! Face them?', # 37B (cut 20)

    # 33: arena#86 (57B) NP: ['Eltia', 'Van']
    'arena#86': 'Van Eltia captain arrives with her crew!', # 39B (cut 18)

    # 34: arena#4 (56B) NP: ['Two']
    'arena#4': 'Two challengers call out! Face them?', # 36B (cut 20)

    # 35: arena#2 (52B) NP: []
    'arena#2': 'A challenger calls out! Face them?', # 34B (cut 18)

    # Titles
    'arena#11': 'Justice and Chivalry',
    'arena#15': 'Items? I have them!',
    'arena#137': 'Secret Longing Blade',
    'arena#226': 'Old Times Guardian',
    'arena#10': 'Mask of Truth & Lies',
    'arena#131': 'Overlord & His Blade',
    'arena#162': 'Like Father & Child?',
    'arena#36': 'Champion Arrives!',
    'arena#57': 'Beauty & the Beast?',
    'arena#66': 'Friends and Rivals',
}

out = {}
for x in itens:
    k = x['id']
    en = x['en']
    if k in overrides:
        s = overrides[k]
        if len(s) < len(en):
            out[k] = s

with open('lotes_corte3/ARENA3_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=True)

print(f"Generated {len(out)} items in lotes_corte3/ARENA3_out.json")
valida('lotes_corte3/ARENA3.json', 'lotes_corte3/ARENA3_out.json')

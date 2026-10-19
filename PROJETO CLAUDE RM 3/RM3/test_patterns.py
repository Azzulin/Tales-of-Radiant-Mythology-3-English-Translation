import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']
orig = {x['id']: x for x in itens}

patterns = [
    (r'^A skill that attaches a talisman reducing enemy (\w+) for a short time with a set chance\.$',
     r'Attaches a talisman briefly reducing enemy \1 by chance.'),
    (r'^Secret arte: flings a talisman reducing enemy (\w+) for a short time with a set chance\.$',
     r'Secret arte: flings a talisman briefly reducing enemy \1 by chance.'),
    (r'^The recipe for "(.*?)" that Coda is yearning for\.$',
     r'Recipe for "\1" that Coda yearns for.'),
    (r'^Title given to someone who ', 'Title for one who '),
    (r'^Title given to ', 'Title for '),
    (r'^An arcane arte where ', 'Arcane arte: '),
    (r'^An arcane arte with ', 'Arcane arte: '),
    (r'^An arcane arte of ', 'Arcane arte: '),
    (r'^An arcane arte that, ', 'Arcane arte: '),
    (r'^An arcane arte that ', 'Arcane arte: '),
    (r'^A fire arte where ', 'Fire arte: '),
    (r'^A short-range skill that ', 'Short-range skill: '),
    (r'^A space-time sword arcane arte that ', 'Space-time sword arcane arte: '),
    (r'^A space-time sword secret arte that ', 'Space-time sword secret arte: '),
    (r'^A wind-element secret arte that ', 'Wind secret arte: '),
    (r'^A skill that ', ''), # will capitalize
    (r'while moving at high speed', 'at high speed'),
    (r'for a short time with a set chance', 'briefly by chance'),
    (r'with a high probability of stunning them', 'with high stun chance'),
    (r'featuring the ability to ', 'able to '),
    (r'\(area of effect in battle\)', '(in battle)'),
    (r'area of effect in battle', 'in battle'),
    (r'for a single target ally', 'for an ally'),
    (r'for a target ally', 'for an ally'),
    (r'for a single ally', 'for an ally'),
    (r'releases gathered fighting spirit', 'releases fighting spirit'),
    (r'in rapid succession', 'rapidly'),
    (r'two more vacuum wave strikes', 'two vacuum strikes'),
    (r'follows up with ', 'follows with '),
    (r'sweeps enemies away with ', 'sweeps enemies with '),
    (r'draws enemies into ', 'draws enemies to '),
    (r'slashes enemies skyward with ', 'slashes foes skyward with '),
    (r'closes distance while unleashing ', 'closes in, unleashing '),
    (r'closes distance instantly, ', 'closes instantly, '),
    (r'delivers consecutive attacks from ', 'attacks consecutively from '),
    (r'executes consecutive attacks from ', 'attacks consecutively from '),
    (r'executes high-speed spinning slashes ', 'executes high-speed spins '),
    (r'thrusts enemies skyward, ', 'thrusts foes skyward, '),
    (r'delivers left and right slashes ', 'delivers dual slashes '),
    (r'knocks down opponents by ', 'knocks down foes by '),
    (r'attacks surrounding enemies with ', 'attacks surrounding foes with '),
    (r'moves broadly while slicing enemies as if dancing through the heavens', 'slices enemies as if dancing through the heavens'),
    (r'slashes enemies like a fluttering swallow, kicking them up at the end', 'slashes like a fluttering swallow, kicking foes up'),
    (r'launches enemies with sword combos and transitions to sheathed stance', 'launches foes with combos, transitioning to sheathed stance'),
]

out = {}
for x in itens:
    s = x['en']
    for pat, rep in patterns:
        if pat == r'^A skill that ':
            if s.startswith('A skill that '):
                rest = s[len('A skill that '):]
                s = rest[0].upper() + rest[1:]
        else:
            s = re.sub(pat, rep, s)
    
    # check if modified
    if s != x['en']:
        out[x['id']] = s

print(f"Items modified: {len(out)} / {len(itens)}")
from val_check import validate_dict
validate_dict('dados/item_equip_shrink/VAL-01.json', out)

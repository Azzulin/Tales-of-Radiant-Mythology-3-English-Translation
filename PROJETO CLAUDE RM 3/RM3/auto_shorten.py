import json, re
from val_check import nomes_proprios, CAUDA

def make_rules():
    rules = [
        # Skill prefix
        (r'^A skill that attaches a talisman reducing enemy (\w+) for a short time with a set chance\.$',
         r'Attaches a talisman briefly lowering enemy \1 by chance.'),
        (r'^Secret arte: flings a talisman reducing enemy (\w+) for a short time with a set chance\.$',
         r'Secret arte: flings a talisman briefly lowering enemy \1 by chance.'),
        
        # Recipes
        (r'^The recipe for "(.*?)" that Coda is yearning for\.$',
         r'Recipe for "\1" that Coda craves.'),
        
        # Prefixes
        (r'^An arcane arte where ', 'Arcane arte: '),
        (r'^An arcane arte that, ', 'Arcane arte: '),
        (r'^An arcane arte that ', 'Arcane arte: '),
        (r'^An arcane arte with ', 'Arcane arte: '),
        (r'^An arcane arte of ', 'Arcane arte: '),
        (r'^An arcane arte ', 'Arcane arte: '),
        (r'^A space-time sword arcane arte that ', 'Space-time sword arcane arte: '),
        (r'^A space-time sword secret arte that ', 'Space-time sword secret arte: '),
        (r'^A wind-element secret arte that ', 'Wind secret arte: '),
        (r'^A fire arte where ', 'Fire arte: '),
        (r'^A short-range skill that ', 'Short-range skill: '),
        (r'^An explosive arcane arte that explicitly ', 'Explosive arcane arte: '),
        (r'^An infinite dagger arcane arte that ', 'Infinite dagger arcane arte: '),
        
        # Titles
        (r'^Title given to someone who ', 'Title for one who '),
        (r'^Title given to someone ', 'Title for someone '),
        (r'^Title given to ', 'Title for '),
        
        # Common word / phrase compressions
        (r'for a short time with a set chance', 'briefly by chance'),
        (r'with a high probability of stunning them', 'with high stun chance'),
        (r'while moving at high speed', 'at high speed'),
        (r'high-speed movement', 'high speed'),
        (r'featuring the ability to ', 'able to '),
        (r'\(area of effect in battle\)', '(in battle)'),
        (r'area of effect in battle', 'in battle'),
        (r'for a single target ally', 'for an ally'),
        (r'for a single ally', 'for an ally'),
        (r'for a target ally', 'for an ally'),
        (r'releases gathered fighting spirit', 'releases fighting spirit'),
        (r'in rapid succession', 'rapidly'),
        (r'two more vacuum wave strikes', 'two vacuum strikes'),
        (r'from rapid thrusts', 'from thrusts'),
        (r'three consecutive thrusts', 'three thrusts'),
        (r'consecutive spinning kicks', 'spinning kicks'),
        (r'two-stage slashes', 'two slashes'),
        (r'left and right slashes', 'dual slashes'),
        (r'closes distance while unleashing', 'closes in, unleashing'),
        (r'closes distance instantly,', 'closes instantly,'),
        (r'closes distance,', 'closes in,'),
        (r'slashes enemies skyward with', 'slashes foes skyward with'),
        (r'slashes enemies skyward,', 'slashes foes skyward,'),
        (r'attacks surrounding enemies with', 'attacks surrounding foes with'),
        (r'delivers consecutive attacks from', 'attacks consecutively from'),
        (r'executes consecutive attacks from', 'attacks consecutively from'),
        (r'executes high-speed spinning slashes', 'executes high-speed spin slashes'),
        (r'sweeps enemies away with', 'sweeps enemies with'),
        (r'draws enemies into', 'draws enemies to'),
        (r'knocks down opponents by', 'knocks down foes by'),
        (r'follows up with ', 'follows with '),
        (r'rushes forward swiftly and ', 'rushes forward and '),
        (r'attacks enemies by slamming them with ', 'attacks by slamming foes with '),
        (r'attacks enemies with air pressure generated from ', 'attacks foes with air pressure from '),
        (r'halts enemy movement with a heavy thrust and launches them skyward\.', 'halts enemy with a heavy thrust and launches them skyward.'),
        (r'launches enemies with combos and slams them down with vacuum blades\.', 'launches with combos and slams down with vacuum blades.'),
        (r'rushes forward, launches enemies, and unleashes consecutive slashes\.', 'rushes forward, launches foes, and unleashes rapid slashes.'),
        (r'sweeps enemy feet, launching and following up with explosive blasts\.', 'sweeps enemy feet, launching with explosive blasts.'),
        (r'delivers a single sword flash while closing distance in an instant\.', 'delivers a sword flash while closing distance instantly.'),
        (r'slashes continuously like flowing water, finishing with shockwaves\.', 'slashes like flowing water, finishing with shockwaves.'),
        (r'launches with lightning and drops giant manifested steel onto foes\.', 'launches with lightning, dropping steel onto foes.'),
        (r'thrusts a spear into the ground, raising a water pillar to attack\.', 'thrusts a spear into ground, raising a water pillar.'),
        (r'launches enemies with shockwave slashes and slams down with a cut\.', 'launches with shockwave slashes and slams down with a cut.'),
        (r'launches enemies, then lands spinning kicks and slashes in midair\.', 'launches foes, landing spinning kicks and slashes in air.'),
        (r'launches enemies with a shield bash and chases with sharp thrusts\.', 'launches with a shield bash, chasing with sharp thrusts.'),
        (r'launches enemies sky-high from godspeed upward slashes into kicks\.', 'launches foes high from godspeed upward slashes into kicks.'),
        (r'launches enemies, ascends with spinning slashes, and fires blasts\.', 'launches, ascends with spinning slashes, and fires blasts.'),
        (r'draw enemies in\.', 'draw enemies closer.'),
        (r'in midair', 'in air'),
        (r'sky-high', 'high'),
        (r'consecutive slashes', 'rapid slashes'),
        (r'consecutive upward slashes', 'rapid upward slashes'),
        (r'consecutive downward slashes', 'rapid downward slashes'),
        (r'slashes enemies with ', 'slashes foes with '),
        (r'launches enemies with ', 'launches foes with '),
        (r'launches enemies into the air,', 'launches foes into the air,'),
        (r'launches enemies,', 'launches foes,'),
        (r'attacks enemies with ', 'attacks foes with '),
    ]
    return rules

def shorten_text(s, rules):
    for pat, rep in rules:
        s = re.sub(pat, rep, s)
    if s.startswith('A skill that '):
        rest = s[len('A skill that '):]
        s = rest[0].upper() + rest[1:]
    return s

if __name__ == '__main__':
    d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
    rules = make_rules()
    out = {}
    for x in d['itens']:
        en = x['en']
        s = shorten_text(en, rules)
        if s != en:
            out[x['id']] = s
            
    from val_check import validate_dict
    validate_dict('dados/item_equip_shrink/VAL-01.json', out)

import json, re
from gen_val01 import build_val01
from val_check import validate_dict

out = build_val01()

# Fix the 3 items
out['valuables#885'] = 'Arcane arte: leaves presents at enemy feet after Explosive Thrust Raid.'
out['valuables#779'] = 'Launches foes, follows up in air, and knocks them down.'
out['valuables#749'] = 'Arcane arte: launches foes skyward and follows with sharp thrusts.'

# Additional trims
d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = {x['id']: x['en'] for x in d['itens']}

more_trims = [
    (r'into the air\.', 'into air.'),
    (r'into the air,', 'in air,'),
    (r'into midair', 'in air'),
    (r'from midair', 'from air'),
    (r'and knocks them down\.', ', knocking them down.'),
    (r'and slams them down\.', ', slamming them down.'),
    (r'consecutive thrusts', 'rapid thrusts'),
    (r'consecutive strikes', 'rapid strikes'),
    (r'surrounding enemies', 'surrounding foes'),
    (r'surrounding foes', 'nearby foes'),
    (r'through enemies', 'through foes'),
    (r'pierces through foes', 'pierces foes'),
    (r'and strikes with flashing thrusts\.', 'and flashing thrusts.'),
    (r'delivers left and right slashes', 'delivers dual slashes'),
    (r'with sword combos', 'with combos'),
    (r'three rapid thrusts', 'three thrusts'),
    (r'two vacuum strikes in air\.', 'two vacuum strikes.'),
    (r'high-speed movement slashes', 'high-speed slashes'),
    (r'closes in, unleashing', 'closes in with'),
    (r'attacks surrounding foes with', 'attacks nearby foes with'),
    (r'air pressure generated from a powerful thrust\.', 'air pressure from a thrust.'),
    (r'snipes enemies with ground fragments shattered from aerial strikes\.',
     'snipes foes with fragments from aerial strikes.'),
    (r'detonates one\'s own fighting spirit to blow away nearby foes\.',
     'detonates fighting spirit to blow away nearby foes.'),
    (r'A party gag item, but getting a laugh with it is considered a formidable feat\.',
     'A party gag item, but getting a laugh with it is a feat.'),
    (r'A horrifying item you can never escape\. Beware, as it strikes without warning\.',
     'Horrifying item you cannot escape. Beware, as it strikes suddenly.'),
    (r'A portrait of a child\. The face is blacked out, but only the eyes can be seen\.',
     'Portrait of a child. Face is blacked out, but the eyes can be seen.'),
    (r'A tool used to crush ice\. If found near a bed, proceed with extreme caution\.',
     'Tool to crush ice. If found near a bed, proceed with caution.'),
    (r'Decorated with countless eyes, though the mirror surfaces are painted black\.',
     'Decorated with countless eyes; mirror surfaces are painted black.'),
    (r'Purpose unknown\. Rumor says you\'ll die peering through it like a telescope\.',
     'Purpose unknown. Rumor says you die peering through it like a telescope.'),
    (r'A nice pocket watch, but the hands move at startling speed\. It is harmless\.',
     'A nice pocket watch, but hands move at startling speed. It is harmless.'),
    (r'A lavish item made with mellow grapes\. Grape lovers will ascend to heaven\.',
     'Made with mellow grapes. Grape lovers will ascend to heaven.'),
    (r'An invention devised by humankind to proceed through shopping efficiently\.',
     'An invention devised by humankind to shop efficiently.'),
    (r'Seals a demon that once drove heaven, earth, and the demon realm to ruin\.',
     'Seals a demon that drove heaven, earth, and the demon realm to ruin.'),
    (r'A part from an antique clock destroyed by a grandfather in a fit of rage\.',
     'Part from an antique clock destroyed by a grandfather in rage.'),
    (r'A spherical compass shaped like an eyeball\. The needle spins ceaselessly\.',
     'A compass shaped like an eyeball. The needle spins ceaselessly.'),
    (r'Reverts skin age to just before infancy\. Risks vanishing you completely\.',
     'Reverts skin age to near infancy. Risks vanishing you completely.'),
    (r'A picture of an adorable kitten\. Contains clues on how to eliminate war\.',
     'Picture of an adorable kitten. Contains clues on eliminating war.'),
    (r'A banner bearing a tiger pattern\. Exudes the nobility of the Beast King\.',
     'Banner bearing a tiger pattern. Exudes nobility of the Beast King.'),
    (r'A green jewel obtained from a green chest in the Holy Land of Langriths\.',
     'Green jewel obtained from a green chest in the Holy Land of Langriths.'),
]

for k in list(out.keys()):
    s = out[k]
    for pat, rep in more_trims:
        s = re.sub(pat, rep, s)
    out[k] = s

# Also check unmodified items to see if any more can be added
for item_id, en in itens.items():
    if item_id not in out:
        s = en
        for pat, rep in more_trims:
            s = re.sub(pat, rep, s)
        if s != en:
            out[item_id] = s

validate_dict('dados/item_equip_shrink/VAL-01.json', out)

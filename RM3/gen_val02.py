import json, re
from val_check import nomes_proprios, CAUDA

def build_val02():
    d = json.load(open('dados/item_equip_shrink/VAL-02.json', encoding='utf-8'))
    itens = d['itens']
    
    # Specific hand-crafted overrides for proper-noun or tricky items in VAL-02
    overrides = {
        'valuables#16': "Listen to 'Meeting at the Fountain Plaza' at Claire's place.",
        'valuables#13': "Allows listening to '...have a good rest time' at Claire's.",
        'valuables#37': "Activated DL Quest 'A Closed Heart, A Continuing Future'.",
        'valuables#25': "Key to DL Quest 'A Closed Heart, A Continuing Future'.",
        'valuables#34': "Activated DL Quest 'The Wall That Must Be Overcome'.",
        'valuables#22': "Key to DL Quest 'The Wall That Must Be Overcome'.",
        'valuables#40': "Activated DL Quest 'In Search of the Ultimate Dish'.",
        'valuables#28': "Key to DL Quest 'In Search of the Ultimate Dish'.",
        'valuables#31': "Activated DL Quest 'A Fight That Cannot Be Lost'.",
        'valuables#81': 'Recipe for "Manchu-Han Imperial Feast" that Coda craves.',
        'valuables#78': 'Recipe for "Medicinal Champuru" that Coda craves.',
        'valuables#69': 'Recipe for "Black Tea Cookies" that Coda craves.',
        'valuables#266': 'White jewel from a green chest in the Rhubarb Mountains.',
        'valuables#272': 'Blue jewel from a green chest in the Sifno Spring Cave.',
        'valuables#269': 'Red jewel from a green chest in the Almanac Ruins.',
        'valuables#2156': 'Heard voice of the Origin World Tree and learned beginnings.',
        'valuables#2368': "Title for one who obtained the Great Swordsman's Radiance.",
        'valuables#2420': "Title for one who obtained the Twin Swordsman's Radiance.",
        'valuables#2416': "Title for one who obtained the Magic Knight's Radiance.",
        'valuables#2364': "Title for one who obtained the Swordsman's Radiance.",
        'valuables#2257': "Title for one who adventures in world's unexplored regions.",
        'valuables#2253': "Title for one who travels to world's unexplored regions.",
        'valuables#2346': 'Title for one who repeatedly flees in the face of enemies.',
        'valuables#2276': 'Title for one who gained an irreplaceable comrade-in-arms.',
        'valuables#2280': 'Title for one who seems to have no financial worries.',
        'valuables#150': 'Lets you see at night as in daylight. Not for weird uses.',
        'valuables#84': 'Passionately builds a romantic mood between couples... or not.',
        'valuables#89': 'In other words, a candle. How it is used depends on the user.',
        'valuables#216': 'Proof obtained only by one who conquered the sealed land.',
        'valuables#177': 'Features an image sketch looking far creepier than needed.',
        'valuables#2329': 'Becomes extremely prone to monster symbol ambushes.',
        'valuables#222': 'A tablet with numbers encrypting the world\'s entire "past".',
        'valuables#1305': "Slams in super fighting spirit to revive a KO'd companion.",
        'valuables#1806': 'Arcane arte: three-hit combos that cleave through evil.',
        'valuables#1094': 'Arcane arte: Twin Spinning Fangs and Crouching Dragon Strike.',
        'valuables#1020': 'Arcane arte: Explosive Shatter Slash and Twin Soaring Moon.',
        'valuables#1088': 'Arcane arte: Twin Spinning Fangs and Flowing Shadow Strike.',
        'valuables#1279': 'Secret arte: slashes up with Crescent Slash and unleashes Beast.',
        'valuables#1800': 'Arcane arte: connects rapid three-hit combos into Beast.',
        'valuables#620': 'Arcane arte: unleashes rapid thrusts, finishing with Beast.',
        'valuables#1405': 'Arcane arte: shoots guns while distracting with Pow Hammer.',
        'valuables#735': 'Arcane arte: follows Dragon Swarm with spin kicks.',
        'valuables#873': 'Secret arte: delivers rapid slashes in air after Soaring Blade.',
        'valuables#1100': 'Secret arte: unleashes shockwaves skyward after Sky Soaring Slash.',
        'valuables#2053': 'Arcane arte: attacks with Charge Bullets exploding up close.',
        'valuables#1102': 'Secret arte: delivers fire-infused slashes after Explosion Sword.',
        'valuables#737': 'Arcane arte: combines Whirling Tornado, Geyser Dragon Strike.',
        'valuables#871': 'Secret arte: delivers rapid slashes in air after Fang Thrust.',
        'valuables#1202': 'Arcane arte: combines Spatial Flight Shift and Void Azure Slash.',
        'valuables#743': 'Arcane arte: combines Whirling Tornado, Explosive Fang Shot.',
        'valuables#1064': 'Arcane arte: Explosive Shatter Slash and Talon Strike.',
        'valuables#1184': 'Arcane arte: connects Tempest into Crescent Flash continuously.',
        'valuables#1392': 'Secret arte: delivers upward kicks and slashes after Fang Edge.',
        'valuables#1204': 'Arcane arte: Lightning Claw Slash and Flashing Blast combo.',
        'valuables#1394': 'Secret arte: executes rapid slashes in air after Wing Edge.',
        'valuables#1445': 'Arcane arte: combines Biting Assault and War Swift Wolf Blast.',
        'valuables#926': 'Arcane arte: combines Wind Blade Binding, Fire Wheel Drop.',
        'valuables#1583': 'Arcane arte: executes three rapid shots of Tree Cannon Flash.',
        'valuables#1575': 'Arcane arte: connects roundhouse kicks into Roaring Shatter.',
        'valuables#1675': 'Arcane arte: Flying Swallow Moon Flower, Crushing Moon Kick.',
        'valuables#1735': 'Arcane arte: follows with downward slashes after Tiger Chaos Kick.',
        'valuables#667': 'Arcane arte: executes a rapid combo on foes after Flashing Blast.',
        'valuables#669': 'Arcane arte: follows with an extra strike after Flashing Blast.',
        'valuables#1104': 'Secret arte: follows with an upward thrust after Flashing Impact.',
    }
    
    rules = [
        # Skill prefix
        (r'^A skill that attaches a talisman reducing enemy (\w+) for a short time with a set chance\.$',
         r'Attaches a talisman briefly lowering enemy \1 by chance.'),
        (r'^Secret arte: flings a talisman reducing enemy (\w+) for a short time with a set chance\.$',
         r'Secret arte: flings a talisman briefly lowering enemy \1 by chance.'),
        (r'^A skill where vacuum waves from high-speed slashes vortex into a flash\.$',
         'Vacuum waves from high-speed slashes vortex into a flash.'),
        (r'^A skill that follows up on three consecutive thrusts with a shield bash\.$',
         'Follows three consecutive thrusts with a shield bash.'),
        (r'^A skill that refines thoughts and fires arrows piercing through enemies\.$',
         'Refines thoughts, firing arrows that pierce through foes.'),
        (r'^A skill that executes three kicks, raises a sword overhead, and slashes\.$',
         'Executes three kicks, raises a sword overhead, and slashes.'),
        (r'^A skill that awakens light thoughts, generating surrounding shockwaves\.$',
         'Awakens light thoughts, generating nearby shockwaves.'),
        (r'^A skill that fires a total of six arrows at high speed from both hands\.$',
         'Fires six arrows at high speed from both hands.'),
        (r'^A skill that blocks enemy physical attacks and delivers counterattacks\.$',
         'Blocks enemy physical attacks and delivers counterattacks.'),
        (r'^A skill that shoots diagonally downward enemies while jumping backward\.$',
         'Shoots downward enemies while jumping backward.'),
        (r'^A skill that slashes upward at the enemy and follows up with a strike\.$',
         'Slashes upward at the enemy and follows with a strike.'),
        (r'^A skill that launches enemies with a spear and strikes with lightning\.$',
         'Launches foes with a spear and strikes with lightning.'),
        (r'^A skill that leaps into the air and attacks enemies with a rapid dive\.$',
         'Leaps into air and attacks foes with a rapid dive.'),
        (r'^A skill that launches enemies with a kick and follows up with gunfire\.$',
         'Launches foes with a kick and follows with gunfire.'),
        (r'^A skill that launches enemies with a shoulder tackle into an uppercut\.$',
         'Launches foes with a shoulder tackle into an uppercut.'),
        (r'^A skill that fires arrows crawling along the ground to target enemies\.$',
         'Fires arrows along the ground to target enemies.'),
        (r'^A skill that draws in enemies, ascends while spinning, and kicks down\.$',
         'Draws in foes, ascends while spinning, and kicks down.'),
        
        # Prefixes
        (r'^An arcane arte where ', 'Arcane arte: '),
        (r'^An arcane arte that, ', 'Arcane arte: '),
        (r'^An arcane arte that ', 'Arcane arte: '),
        (r'^An arcane arte with ', 'Arcane arte: '),
        (r'^An arcane arte of ', 'Arcane arte: '),
        (r'^An arcane arte ', 'Arcane arte: '),
        (r'^A wind-element secret arte that ', 'Wind secret arte: '),
        
        # Titles
        (r'^Title given to someone who ', 'Title for one who '),
        (r'^Title given to someone ', 'Title for someone '),
        (r'^Title given to ', 'Title for '),
        
        # AoE
        (r'\(area of effect in battle\)', '(in battle)'),
        (r'area of effect in battle', 'in battle'),
        (r'for a single target ally', 'for an ally'),
        (r'for a single ally', 'for an ally'),
        (r'for a target ally', 'for an ally'),
        (r'for a set time\.', 'temporarily.'),
        (r'for a set time', 'temporarily'),
        (r'for a short time', 'briefly'),
        (r'beneath the target enemy\.', 'beneath target foe.'),
        (r'around the target enemy\.', 'around target foe.'),
        (r'at the target enemy\'s position\.', 'at target foe.'),
        (r'toward the target enemy\.', 'toward target foe.'),
        (r'absorbs HP from enemies in range to restore the caster\'s own HP\.',
         'absorbs HP from nearby enemies to restore caster\'s HP.'),
    ]
    
    extra_trims = [
        (r'closing distance', 'closing in'),
        (r'spinning slashes', 'spin slashes'),
        (r'spinning kicks', 'spin kicks'),
        (r'spinning impacts', 'spin impacts'),
        (r'through enemies', 'through foes'),
        (r'enemies with', 'foes with'),
        (r'into enemies', 'into foes'),
        (r'attacks enemies', 'attacks foes'),
        (r'slashes enemies', 'slashes foes'),
        (r'launches enemies', 'launches foes'),
        (r'surrounding foes', 'nearby foes'),
        (r'surrounding enemies', 'nearby foes'),
        (r'the surroundings', 'nearby area'),
        (r'toward the heavens', 'skyward'),
        (r'high into the sky', 'skyward'),
        (r'consecutive attacks', 'rapid attacks'),
        (r'consecutive slashes', 'rapid slashes'),
        (r'consecutive thrusts', 'rapid thrusts'),
        (r'in an instant', 'instantly'),
        (r'on enemies', 'on foes'),
        (r'to enemies', 'to foes'),
        (r'striking enemies', 'striking foes'),
        (r'impales enemies', 'impales foes'),
        (r'draws enemies', 'draws foes'),
        (r'draw in enemies', 'draw foes in'),
        (r'sweeps enemies', 'sweeps foes'),
        (r'and strikes with shockwaves', 'with shockwaves'),
        (r'and finishes with ', ', finishing with '),
        (r'and connects into ', ', connecting into '),
        (r'to attack foes\.', 'to attack.'),
        (r'to attack enemies\.', 'to attack.'),
        (r'follows up with ', 'follows with '),
        (r'follows up on ', 'follows '),
        (r'follows up in ', 'follows in '),
        (r'follows up,', 'follows,'),
        (r'two-stage strikes', 'two strikes'),
        (r'from impact points', 'on impact'),
        (r'in rapid succession', 'rapidly'),
        (r'in midair', 'in air'),
        (r'from midair', 'from air'),
        (r'into the air', 'into air'),
        (r'into midair', 'in air'),
        (r'sky-high', 'high'),
        (r'at high speed', 'at high speed'),
    ]
    
    out = {}
    for x in itens:
        item_id = x['id']
        en = x['en']
        if item_id in overrides:
            s = overrides[item_id]
        else:
            s = en
            for pat, rep in rules:
                s = re.sub(pat, rep, s)
            if s.startswith('A skill that '):
                rest = s[len('A skill that '):]
                s = rest[0].upper() + rest[1:]
        
        for pat, rep in extra_trims:
            s = re.sub(pat, rep, s)
        
        if s != en:
            out[item_id] = s
            
    return out

if __name__ == '__main__':
    out = build_val02()
    print(f"Total entries in out: {len(out)}")
    from val_check import validate_dict
    ok = validate_dict('dados/item_equip_shrink/VAL-02.json', out)
    if ok:
        with open('dados/item_equip_shrink/VAL-02_out.json', 'w', encoding='utf-8') as f:
            json.dump(out, f, indent=1, ensure_ascii=True)
        print("SAVED VAL-02_out.json!")

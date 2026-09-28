import json, re
from val_check import validate_dict, nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
items = d['itens']

# Let's inspect the sentences and apply smart, idiomatic shortening functions.
def shorten_line(id_str, old_en, jp):
    t = old_en
    # Common prefixes
    t = re.sub(r'^An arcane arte where ', 'Arcane arte: ', t)
    t = re.sub(r'^An arcane arte that ', 'Arcane arte: ', t)
    t = re.sub(r'^A secret arte where ', 'Secret arte: ', t)
    t = re.sub(r'^A secret arte that ', 'Secret arte: ', t)
    t = re.sub(r'^An arte where ', 'Arte: ', t)
    t = re.sub(r'^An arte that ', 'Arte: ', t)
    t = re.sub(r'^A skill that ', 'Skill: ', t)
    t = re.sub(r'^A fire arte where ', 'Fire arte: ', t)
    t = re.sub(r'^A water arte where ', 'Water arte: ', t)
    t = re.sub(r'^An earth arte where ', 'Earth arte: ', t)
    t = re.sub(r'^A wind arte where ', 'Wind arte: ', t)
    t = re.sub(r'^A light arte where ', 'Light arte: ', t)
    t = re.sub(r'^A dark arte where ', 'Dark arte: ', t)
    
    # Common patterns
    t = re.sub(r'for a short time with a set chance\.', 'with a chance to briefly take effect.', t)
    t = re.sub(r'reducing enemy (\w+) for a short time with a set chance\.', r'with a chance to briefly lower enemy \1.', t)
    t = re.sub(r'increasing ally (\w+) for a short time with a set chance\.', r'with a chance to briefly boost ally \1.', t)
    t = re.sub(r'with a set chance to inflict (\w+)\.', r'with a chance to inflict \1.', t)
    t = re.sub(r'featuring the ability to ', 'allowing one to ', t)
    t = re.sub(r'while moving at high speed, ', 'at high speed, ', t)
    t = re.sub(r'for a certain period of time\.', 'temporarily.', t)
    t = re.sub(r'for a short time\.', 'briefly.', t)
    t = re.sub(r'for a long time\.', 'for long.', t)
    t = re.sub(r'with spinning impacts', 'with spin impacts', t)
    t = re.sub(r'from the impact of ', 'by ', t)
    t = re.sub(r'A key that unlocks the door to ', 'Key unlocking door to ', t)
    t = re.sub(r'A key used to make contact with other worlds\.', 'Key used to contact other worlds.', t)
    
    return t

print("Loaded test harness")

import json
from val_check import validate_dict

d = json.load(open('lotes_corte3/ENH3.json', encoding='utf-8'))
itens = d['itens']
meta = d['meta_bytes_a_cortar']

replacements = {
    'enhance_material#143': 'A bone possessing a lingering will even after death.',
    'enhance_material#116': 'A degraded feather shed naturally after serving its purpose.',
    'enhance_material#173': 'A tentacle hunting for prey even after being severed.',
    'enhance_material#20': 'A quartz family gemstone emitting soft, varied colors.',
    'enhance_material#71': 'A beak cited as evidence of environmental pollution.',
    'enhance_material#164': 'A tentacle still moving even after severed from the body.',
    'enhance_material#68': 'A scale gleams bright enough to be mistaken for a jewel.',
    'enhance_material#98': 'A whisker that appears and vanishes, yet definitely exists.',
    'enhance_material#92': 'A firm, springy whisker that does not waver in the wind.',
    'enhance_material#113': 'A hide so elegant it feels presumptuous to even behold.',
    'enhance_material#38': 'A fiber said to be dropped by unidentified craft.',
    'enhance_material#152': 'A needle containing lethal venom that kills on piercing.',
    'enhance_material#83': 'A tenacious beak that has devoured all kinds of things.',
    'enhance_material#53': 'A fang evoking commanding presence of its owner.',
    'enhance_material#59': 'A scale that protected against outside environment.',
    'enhance_material#122': 'A feather serving as deciding factor in courtship.',
    'enhance_material#140': 'A bone steeped in bitter grudges from past life.',
    'enhance_material#170': 'A tentacle dripping with sluggish slime.',
    'enhance_material#89': 'A supple tail swaying gently back and forth.',
    'enhance_material#149': 'A needle hard to pull out once it pierces.',
}

out = {}
for x in itens:
    item_id = x['id']
    if item_id in replacements:
        out[item_id] = replacements[item_id]

with open('lotes_corte3/ENH3_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=True)
print("Saved ENH3_out.json!")

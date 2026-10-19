import json, re
from val_check import nomes_proprios, CAUDA

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']

# Test rule-based candidate generator
candidates = {}
unhandled = []

for x in itens:
    item_id = x['id']
    en = x['en']
    need = x['bytes'] - x['alvo_bytes']
    s = en
    
    # Check if we can apply clean syntactic simplifications
    # 1. Talismans:
    # "A skill that attaches a talisman reducing enemy ([a-z]+) for a short time with a set chance."
    # "Secret arte: flings a talisman reducing enemy ([a-z]+) for a short time with a set chance."
    m = re.match(r'^A skill that attaches a talisman reducing enemy (\w+) for a short time with a set chance\.$', s)
    if m:
        stat = m.group(1)
        s = f"Attaches a talisman briefly lowering enemy {stat} by chance."
    
    m = re.match(r'^Secret arte: flings a talisman reducing enemy (\w+) for a short time with a set chance\.$', s)
    if m:
        stat = m.group(1)
        s = f"Secret arte: flings a talisman briefly lowering enemy {stat}."

    # 2. "An arcane arte where " -> "Arcane arte: "
    if s.startswith("An arcane arte where "):
        s = "Arcane arte: " + s[len("An arcane arte where "):]
    elif s.startswith("An arcane arte with "):
        s = "Arcane arte: with " + s[len("An arcane arte with "):]
    elif s.startswith("An arcane arte of "):
        s = "Arcane arte: " + s[len("An arcane arte of "):]
    elif s.startswith("An arcane arte that, "):
        s = "Arcane arte: " + s[len("An arcane arte that, "):]
    elif s.startswith("An arcane arte that "):
        s = "Arcane arte: " + s[len("An arcane arte that "):]
    elif s.startswith("A fire arte where "):
        s = "Fire arte: " + s[len("A fire arte where "):]
    elif s.startswith("A short-range skill that "):
        s = "Short-range skill: " + s[len("A short-range skill that "):]
    elif s.startswith("A space-time sword arcane arte that "):
        s = "Space-time sword arcane arte: " + s[len("A space-time sword arcane arte that "):]
    elif s.startswith("A space-time sword secret arte that "):
        s = "Space-time sword secret arte: " + s[len("A space-time sword secret arte that "):]
    elif s.startswith("A wind-element secret arte that "):
        s = "Wind secret arte: " + s[len("A wind-element secret arte that "):]

    # 3. "A skill that " -> strip and capitalize
    if s.startswith("A skill that "):
        rest = s[len("A skill that "):]
        s = rest[0].upper() + rest[1:]

    # 4. Recipes:
    # 'The recipe for "X" that Coda is yearning for.' -> 'Recipe for "X" that Coda yearns for.'
    m = re.match(r'^The recipe for "(.*?)" that Coda is yearning for\.$', s)
    if m:
        dish = m.group(1)
        s = f'Recipe for "{dish}" that Coda yearns for.'

    # 5. "Title given to someone who " -> "Title for someone who "
    if s.startswith("Title given to someone who "):
        s = "Title for one who " + s[len("Title given to someone who "):]

    cut = len(en) - len(s)
    candidates[item_id] = (s, cut, need)

print("Generated candidates for", len(candidates), "items")
good = 0
total_cut = 0
for item_id, (s, cut, need) in candidates.items():
    if cut > 0:
        good += 1
        total_cut += cut
print(f"Items cut: {good} / {len(itens)}, total cut so far: {total_cut} / 3447")

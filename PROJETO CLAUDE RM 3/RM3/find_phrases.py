import json, re
from collections import Counter

d = json.load(open('dados/item_equip_shrink/VAL-01.json', encoding='utf-8'))
itens = d['itens']

phrases = Counter()
for x in itens:
    words = re.findall(r"\b[A-Za-z']+\b", x['en'])
    for n in [2, 3, 4]:
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n]).lower()
            phrases[phrase] += 1

for phrase, count in phrases.most_common(50):
    if count >= 3:
        print(f"{count:2d}x: {phrase}")

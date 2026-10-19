import csv, re

# Translation table for all 231 lines of SHIELD.tsv
# id -> (translation, note)
T = {
    # 0-15: Locations
    'shield#0': ('Arena', 'Coliseu/Arena (max 6)'),
    'shield#1': ('World Map', ''),
    'shield#2': ('Debug Room', ''),
    'shield#3': ('Van Eltia', ''),
    'shield#4': ('Mt. Rhubarb', 'Rhubarb Mountains'),
    'shield#5': ('Confeito Forest', 'Confeito Great Forest'),
    'shield#6': ('Brownie Mine', ''),
    'shield#7': ('Mt. Alterata', 'Alterata Volcano curto'),
    'shield#8': ('Kadaif Desert', ''),
    'shield#9': ('Almanac Ruins', ''),
    'shield#10': ('Mt. Absol', ''),
    'shield#11': ('Veratropa', ''),
    'shield#12': ('Sifno Spring', 'Sifno Spring Cave curto'),
    'shield#13': ('Holy Langriths', 'Langriths'),
    'shield#14': ('Elan Vital', ''),
    'shield#15': ('Memory Mine', 'Mine of Reminiscence curto'),

    # 16-19
    'shield#16': ('Buckler', ''),
    'shield#17': ('A light shield with great defense.', ''),
    'shield#18': ('Small Shield', ''),
    'shield#19': ('Compact.', '小型の盾 (max 8)'),

    # 20-22: Aluminum pot lid
    'shield#20': ('Alum Pot Lid', 'アルミ鍋のふた (max 15)'),
    'shield#21': ('Alum Pot Lid', 'leitura kana'),
    'shield#22': ('An alum pot lid.', 'アルミ製の鍋のふた (max 19)'),

    # 23-26
    'shield#23': ('Wood Shield', ''),
    'shield#24': ('Wooden.', '木製の盾 (max 8)'),
    'shield#25': ('Round Shield', ''),
    'shield#26': ('Round.', '丸形の盾 (max 8)'),

    # 27-30
    'shield#27': ('Iron Shield', ''),
    'shield#28': ('Iron shield.', '鉄製のシールド (max 15)'),
    'shield#29': ('Large Shield', ''),
    'shield#30': ('Large shield. Blocks better than small.', '大型の盾 (max 45)'),

    # 31-36
    'shield#31': ('Kite Shield', ''),
    'shield#32': ('Kite-shape shield.', '逆三角形の凧型の盾 (max 19)'),
    'shield#33': ('Needle Shield', ''),
    'shield#34': ('A shield adorned with needles.', ''),
    'shield#35': ('Tower Shield', ''),
    'shield#36': ('A huge shield set on the ground to use.', ''),

    # 37-39: Tortoise shell shield
    'shield#37': ('Carapace', '甲羅の盾 (max 8)'),
    'shield#38': ('Carapace', 'leitura kana'),
    'shield#39': ('Turtle shell shield.', '大亀の甲羅から作られた盾 (max 26)'),

    # 40-45
    'shield#40': ('Marvel Shield', ''),
    'shield#41': ('Modeled on ancient lore.', '昔話に登場した盾を模したもの (max 30)'),
    'shield#42': ('Prayer Shield', ''),
    'shield#43': ('Shield shaped like prayer mask.', '祈祷の為に作られた仮面を模した盾 (max 35)'),
    'shield#44': ('Soldier Shield', ''),
    'shield#45': ('Favored by troops.', '兵士が好んで使う盾 (max 19)'),

    # 46-51
    'shield#46': ('Gothic Shield', ''),
    'shield#47': ('A shield boasting both defense and beauty.', ''),
    'shield#48': ('Battle Shield', ''),
    'shield#49': ('Crafted for combat.', '戦闘用に開発された盾 (max 21)'),
    'shield#50': ('Metal Shield', ''),
    'shield#51': ('Versatile steel shield.', '鋼鉄で鍛えられた汎用的な盾 (max 28)'),

    # 52-55
    'shield#52': ('Iron Cover Shield', ''),
    'shield#53': ('Wood shield plated in metal.', '金属板で強化されたウッドシールド (max 35)'),
    'shield#54': ('Beast Shield', ''),
    'shield#55': ('Shield with beast visage.', '獣の面をあしらったシールド (max 28)'),

    # 56-59
    'shield#56': ('Prince Shield', ''),
    'shield#57': ('Made for a prince at war.', '戦いに赴く王子の為に作られた盾 (max 32)'),
    'shield#58': ('Princess Shield', ''),
    'shield#59': ('Made for princess at war.', '戦いに赴く王女の為に作られた盾 (max 32)'),

    # 60-63
    'shield#60': ('Power Stone Shield', ''),
    'shield#61': ('A shield adorned with lucky stones.', ''),
    'shield#62': ('Eunomia Shield', ''),
    'shield#63': ('A shield meaning order, a goddess aspect.', ''),

    # 64-67
    'shield#64': ('Large Bone Shield', ''),
    'shield#65': ('Large shield of monster bone.', '魔物の骨で作られたラージシールド (max 35)'),
    'shield#66': ('Devil Shield', ''),
    'shield#67': ('Shield with a demon face.', '悪魔の妖面があしらわれた盾 (max 28)'),

    # 68-71
    'shield#68': ('Great Buckler', ''),
    'shield#69': ('Buckler bolstered with steel.', '鋼鉄板で防御力を上げたバックラー (max 35)'),
    'shield#70': ('Silver Small', ''),
    'shield#71': ('Small shield of silver.', '銀製のスモールシールド (max 24)'),

    # 72-74: Copper pot lid
    'shield#72': ('Copper Lid', '銅鍋のふた (max 11)'),
    'shield#73': ('Copper Lid', 'leitura kana'),
    'shield#74': ('Copper pot lid.', '銅製の鍋のふた (max 15)'),

    # 75-80
    'shield#75': ('Oak Shield', ''),
    'shield#76': ('Stout shield of oak.', 'オーク材を使った堅牢な盾 (max 26)'),
    'shield#77': ('Moon Shield', ''),
    'shield#78': ('Shield of the moon.', '月をモチーフにした盾 (max 21)'),
    'shield#79': ('Silver Shield', ''),
    'shield#80': ('Silver shield.', '銀製のシールド (max 15)'),

    # 81-84
    'shield#81': ('Army Shield', ''),
    'shield#82': ('Infantry large shield.', '歩兵が使用していた大型盾 (max 26)'),
    'shield#83': ('Knight Shield', ''),
    'shield#84': ('Shield favored by knights.', 'その昔騎士が好んで使用した盾 (max 30)'),

    # 85-88
    'shield#85': ('Spike Shield', ''),
    'shield#86': ('A shield with giant spikes made for shock troops.', ''),
    'shield#87': ('Full Tower Shield', ''),
    'shield#88': ('Huge shield. Takes great strength to wield.', '超大型の盾 (max 48)'),

    # 89-91: Fine shell shield
    'shield#89': ('Fine Carapace', '上質な甲羅の盾 (max 15)'),
    'shield#90': ('Fine Carapace', 'leitura kana'),
    'shield#91': ('Shield of fine turtle shell.', '上質な大亀の甲羅から作られた盾 (max 32)'),

    # 92-95
    'shield#92': ('Alice Shield', ''),
    'shield#93': ('Modeled on fairy tale shield.', 'おとぎ話に登場した盾を模したもの (max 35)'),
    'shield#94': ('Shaman Shield', ''),
    'shield#95': ('A shield shaped like a shaman ritual mask.', ''),

    # 96-98: Middle S Shield
    'shield#96': ('Middle S Shield', ''),
    'shield#97': ('Middle S Shield', 'leitura kana'),
    'shield#98': ('Favored by elite soldiers.', '階級の高い兵士が好んで使う盾 (max 30)'),

    # 99-102
    'shield#99': ('Emboss Shield', ''),
    'shield#100': ('Carved in ancient style.', '古代様式の文様を施した盾 (max 26)'),
    'shield#101': ('Duel Shield', ''),
    'shield#102': ('Shield refined for duels.', '決闘用として改良を施された盾 (max 30)'),

    # 103-106
    'shield#103': ('High Metal Shield', ''),
    'shield#104': ('Versatile shield of hard metal.', '硬度の高い金属で鍛えられた汎用的な盾 (max 39)'),
    'shield#105': ('Aluminum Cover', ''),
    'shield#106': ('A wood shield reinforced with stronger metal.', ''),

    # 107-112
    'shield#107': ('Lionheart', ''),
    'shield#108': ('Stout shield with a lion soul.', '百獣の王ライオンの魂 (max 43)'),
    'shield#109': ('King Shield', ''),
    'shield#110': ('Forged for a king at war.', '戦いに赴く王の為に作られた盾 (max 30)'),
    'shield#111': ('Queen Shield', ''),
    'shield#112': ('Forged for queen at war.', '戦いに赴く女王の為に作られた盾 (max 32)'),

    # 113-118
    'shield#113': ('Jewel Shield', ''),
    'shield#114': ('A shield decorated with lucky gemstones.', ''),
    'shield#115': ('Dike Shield', ''),
    'shield#116': ('A shield meaning fate, a goddess aspect.', ''),
    'shield#117': ('Huge Bone Shield', ''),
    'shield#118': ('A large shield crafted from hard monster bone.', ''),

    # 119-122
    'shield#119': ('Demon Shield', ''),
    'shield#120': ('Archdemon face causes dread.', '大悪魔の面が見る者を畏怖させる (max 32)'),
    'shield#121': ('Heavy Buckler', ''),
    'shield#122': ('Buckler of steel.', '鋼鉄製のバックラー (max 19)'),

    # 123-127: Molybdenum steel pot lid
    'shield#123': ('Mithril Small', ''),
    'shield#124': ('Small shield of mithril.', 'ミスリル製のスモールシールド (max 30)'),
    'shield#125': ('Moly Steel Pot Lid', ''),
    'shield#126': ('Moly Steel Pot Lid', 'leitura kana'),
    'shield#127': ('Pot lid of moly steel.', 'モリブデン鋼製の鍋のふた (max 26)'),

    # 128-133
    'shield#128': ('Large Oak Shield', ''),
    'shield#129': ('Large, stout oak shield.', 'オーク材を使った堅牢かつ大型の盾 (max 35)'),
    'shield#130': ('Rune Shield', ''),
    'shield#131': ('Moon shield carved with runes.', 'ムーンシールドに魔法文様を施した盾 (max 37)'),
    'shield#132': ('Mithril Shield', ''),
    'shield#133': ('Mithril shield.', 'ミスリル製のシールド (max 21)'),

    # 134-139
    'shield#134': ('Master Shield', ''),
    'shield#135': ('Large shield wielded by veterans.', '戦闘の熟練者が使っていたとされる大型盾 (max 41)'),
    'shield#136': ('Paladin Shield', ''),
    'shield#137': ('Used by holy knights.', '聖騎士が使用していた盾 (max 24)'),
    'shield#138': ('Spartacus', ''),
    'shield#139': ('Duel shield from arena of old.', '古代の闘技場で使われた決闘用の盾 (max 35)'),

    # 140-144: Millennial turtle shield
    'shield#140': ('Fortress', ''),
    'shield#141': ('Fortress guard.', '要塞防御用の盾 (max 15)'),
    'shield#142': ('Aegis Sh.', '千年亀の盾 (max 11)'),
    'shield#143': ('Aegis Sh.', 'leitura kana'),
    'shield#144': ('Shield of 1,000-year turtle.', '千年生きた大亀の甲羅から作られた盾 (max 37)'),

    # 145-148
    'shield#145': ('Fairy Shield', ''),
    'shield#146': ('Modeled on heroic legend.', '英雄譚に登場した盾を模したもの (max 32)'),
    'shield#147': ('Necromancer Shield', ''),
    'shield#148': ('Shield styled as rebirth ritual mask.', '死者の復活の儀式に用いられた仮面 (max 45)'),

    # 149-153: Master S Shield
    'shield#149': ('Master S Shield', ''),
    'shield#150': ('Master S Shield', 'leitura kana'),
    'shield#151': ('Combat shield beloved by veterans.', '歴戦の戦士が愛用する実戦にとても適した盾 (max 43)'),
    'shield#152': ('Ancient Shield', ''),
    'shield#153': ('Legend.', '伝説の盾 (max 8)'),

    # 154-159
    'shield#154': ('War Shield', ''),
    'shield#155': ('Wartime masterwork surviving many wars.', '戦時中に使われたとされる歴戦を勝ち残った名品 (max 48)'),
    'shield#156': ('Rare Metal Shield', ''),
    'shield#157': ('Versatile shield of rare steel.', '希少な鋼鉄で鍛えられた汎用的な盾 (max 35)'),
    'shield#158': ('Titanium Cover', ''),
    'shield#159': ('Wood shield clad in extra strong metal.', '更に強度の高い金属で強化されたウッドシールド (max 48)'),

    # 160-165
    'shield#160': ('King of Beasts', ''),
    'shield#161': ('A masterwork engraved with the sovereign lion king.', ''),
    'shield#162': ('Emperor Shield', ''),
    'shield#163': ('Made for an emperor at war.', '戦いに赴く皇帝の為に作られた盾 (max 32)'),
    'shield#164': ('Empress Shield', ''),
    'shield#165': ('Made for an empress at war.', '戦いに赴く女帝の為に作られた盾 (max 32)'),

    # 166-171
    'shield#166': ('Orb Shield', ''),
    'shield#167': ('Shield set with lucky stones.', '運気を上げるとされる魔石をあしらった盾 (max 41)'),
    'shield#168': ('Eirene Shield', ''),
    'shield#169': ('A shield meaning peace, a goddess aspect.', ''),
    'shield#170': ('Ancient Bone', ''),
    'shield#171': ('Rugged shield of ancient bones.', '古生代の魔物の骨で作られた屈強なシールド (max 43)'),

    # 172-177: Arch D Shield & Descender Warrior Shield
    'shield#172': ('Arch D Shield', ''),
    'shield#173': ('Arch D Shield', 'leitura kana'),
    'shield#174': ('Dread shield scaring even fiends.', '上級悪魔の妖面が魔物すら怯えさせる脅威の盾 (max 45)'),
    'shield#175': ('Warrior', '戦士の盾 (max 8)'),
    'shield#176': ('Warrior', 'leitura kana'),
    'shield#177': ('Shield for Descender warriors.', 'ディセンダーと認められた戦士専用の盾 (max 39)'),

    # 178-183: Swordsman & Magic Swordsman
    'shield#178': ('Swordsmn', '剣士の盾 (max 8)'),
    'shield#179': ('Swordsmn', 'leitura kana'),
    'shield#180': ('Shield for Descender swordsmen.', 'ディセンダーと認められた剣士専用の盾 (max 39)'),
    'shield#181': ('Spellblade', '魔法剣士の盾 (max 13)'),
    'shield#182': ('Spellblade', 'leitura kana'),
    'shield#183': ('Shield for Descender spellblades.', 'ディセンダーと認められた魔法剣士専用の盾 (max 43)'),

    # 184-189: Fighter & Knight
    'shield#184': ('Fighter', '闘士の盾 (max 8)'),
    'shield#185': ('Fighter', 'leitura kana'),
    'shield#186': ('Shield made for Descender warriors.', 'ディセンダーの為に作られた戦士専用の盾 (max 41)'),
    'shield#187': ('Knight', '騎士の盾 (max 8)'),
    'shield#188': ('Knight', 'leitura kana'),
    'shield#189': ('Shield made for Descender swordsmen.', 'ディセンダーの為に作られた剣士専用の盾 (max 41)'),

    # 190-195: Magic Knight & R Line
    'shield#190': ('M. Knight', '魔法騎士の盾 (max 13)'),
    'shield#191': ('M. Knight', 'leitura kana'),
    'shield#192': ('Shield made for Descender spellblades.', 'ディセンダーの為に作られた魔法剣士専用の盾 (max 45)'),
    'shield#193': ('R Line Shield', ''),
    'shield#194': ('Red Line Shield', ''),
    'shield#195': ('Gilgamesh shield with red lines.', '赤いラインが鮮やかな勇者ギルガメシュの盾 (max 43)'),

    # 196-200: B Line & Storm Shield
    'shield#196': ('B Line Shield', ''),
    'shield#197': ('Blue Line Shield', ''),
    'shield#198': ('Gilgamesh shield with blue lines.', '青いラインが鮮やかな勇者ギルガメシュの盾 (max 43)'),
    'shield#199': ('Storm Shield', ''),
    'shield#200': ('Shield repelling any storm.', 'どんな嵐をも防ぐとされる伝説の盾 (max 35)'),

    # 201-205: Dominion & Giri Choco
    'shield#201': ('Dominion', ''),
    'shield#202': ('Winged angel shield of legend.', '幾枚もの羽を持つ主天使の姿をした伝説の盾 (max 43)'),
    'shield#203': ('Friend Choc', 'Giri choco (max 11)'),
    'shield#204': ('Friend Choc', 'leitura kana'),
    'shield#205': ('Token of thanks for kindness.', 'お世話になっている人への感謝の印 (max 35)'),

    # 206-208: Honmei Choco
    'shield#206': ('True Love', 'Honmei choco (max 11)'),
    'shield#207': ('True Love Choc', 'leitura kana (max 15)'),
    'shield#208': ('These feelings, just you.', 'この想いをあなただけに… (max 26)'),

    # 209-214: Wada Don & Wada Katsu
    'shield#209': ('Don-chan', ''),
    'shield#210': ('Don-chan', 'leitura kana'),
    'shield#211': ("Blocking with this makes no 'don!' sound.", ''),
    'shield#212': ('Kat-chan', ''),
    'shield#213': ('Kat-chan', 'leitura kana'),
    'shield#214': ("Blocking with this makes no 'kat!' sound.", ''),

    # 215-216: Flatfish
    'shield#215': ('Flound', 'Hirame (max 6)'),
    'shield#216': ("A fine white fish. Frozen, so it's sturdy.", ''),

    # 217-220: TOS Kratos & TOV Estelle
    'shield#217': ('Rare Shield', ''),
    'shield#218': ('Shield equipped by Kratos from TOS in this game.', ''),
    'shield#219': ('Queen of Hearts', ''),
    'shield#220': ('Shield equipped by Estelle from TOV in this game.', ''),

    # 221-226: Xevious cameos
    'shield#221': ('Andor Genesis', ''),
    'shield#222': ('That fortress of legend is here!', ''),
    'shield#223': ('Toroid', ''),
    'shield#224': ('Classic video game character appears as equipment!', ''),
    'shield#225': ('Bacura', ''),
    'shield#226': ("Won't break even after 256 hits!", ''),

    # 227-230: TOV Flynn & Beam Shield
    'shield#227': ('White Knight Shield', ''),
    'shield#228': ('Shield equipped by Flynn from TOV in this game.', ''),
    'shield#229': ('Beam Shield', ''),
    'shield#230': ('Unknown tech core.', '未知の技術の結晶体 (max 19)'),
}

with open('lotes_p68/SHIELD.tsv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    fieldnames = reader.fieldnames
    rows = list(reader)

missing = []
for r in rows:
    rid = r['id']
    if rid not in T:
        missing.append(rid)
    else:
        tr, nt = T[rid]
        r['traducao'] = tr
        if nt:
            r['nota_do_tradutor'] = nt

if missing:
    print("MISSING IDS:", missing)
else:
    out_p = 'lotes_p68/SHIELD_retorno.tsv'
    with open(out_p, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        w.writeheader()
        w.writerows(rows)
    print("Wrote", out_p)

places = [
    '闘技場', 'ワールドマップ', 'デバッグ部屋', 'バンエルティア号',
    'ルバーブ連山', 'コンフェイト大森林', 'ブラウニー坑道', 'オルタータ火山',
    'カダイフ砂漠', 'アルマナック遺跡', '霊峰アブソール', 'ヴェラトローパ',
    'シフノ湧泉洞', '聖地ラングリース', 'エラン・ヴィタール', '追憶の坑道'
]

import glob, csv

matches = {}
for p in glob.glob('lotes/*_retorno.tsv'):
    with open(p, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            orig = r.get('original', '').strip()
            for plc in places:
                if orig == plc or orig == plc + '　' or orig.startswith(plc):
                    if plc not in matches:
                        matches[plc] = []
                    matches[plc].append((p, orig, r.get('traducao', '').strip()))

for plc in places:
    print(f"=== {plc} ===")
    if plc in matches:
        for item in matches[plc][:3]:
            print(f"  {item[0]} | {item[1]} -> {item[2]}")
    else:
        print("  NO MATCH")

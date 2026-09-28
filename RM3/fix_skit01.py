from build_skit01 import T
import csv

fixes = {
    'skit#71': "Do It Together",
    'skit#73': 'Like Spring',
    'skit#74': 'Tactics Theory',
    'skit#77': 'Rose Blade',
    'skit#78': 'Wild Reunion?',
    'skit#79': 'Indistinct?',
    'skit#82': 'Wise King',
    'skit#84': 'Mealtime',
    'skit#86': 'Yet Adult',
    'skit#93': 'Special Art',
    'skit#101': 'Good Old Rocks',
    'skit#102': 'Ladle Legend',
    'skit#108': 'Sis Toil',
    'skit#114': 'Kyle Sibling',
    'skit#118': 'All Happiness',
    'skit#125': 'New Voice',
    'skit#126': 'Shock Truth',
    'skit#127': 'Shock Truth: Later',
    'skit#128': 'Hot Girls',
    'skit#130': 'Name Meaning',
    'skit#131': 'True Rumor?',
    'skit#132': 'Wary Roni',
    'skit#136': 'Way Hotter',
    'skit#138': 'Training',
    'skit#151': 'Key Study',
    'skit#160': 'Mao Scary Tale',
    'skit#164': 'Study Serious',
    'skit#173': 'Idle Gossip',
    'skit#184': 'Suzu Scary Tale',
    'skit#185': 'Penalty',
    'skit#201': 'Cold!',
    'skit#204': 'Spirit Mood',
    'skit#208': 'Proud Tutor',
    'skit#221': 'Nice Meet!',
    'skit#223': 'Always Close',
    'skit#232': 'Forever',
    'skit#234': 'Teacher Traits',
    'skit#242': 'Good and Evil',
    'skit#243': 'War Ennui',
    'skit#245': 'Dear Days',
    'skit#247': 'Thinking Back..',
    'skit#252': 'Creep!',
    'skit#256': 'Ninja Life',
    'skit#258': 'Clinging',
    'skit#261': 'Quiet Clean Duty',
    'skit#262': 'Charm Power',
    'skit#270': 'Snow Promise',
    'skit#271': 'Bad Luck',
    'skit#272': 'Nightmare!',
    'skit#273': 'Nightmare!: Pt 2',
    'skit#278': 'Complex',
    'skit#280': 'With You, Truly...',
    'skit#287': 'Discerning Man',
    'skit#289': 'Pros & Cons',
    'skit#291': 'Truth',
    'skit#293': 'Unthinkable',
    'skit#297': 'Sly Dog',
    'skit#304': 'War Veterans',
    'skit#311': 'Claire Path',
    'skit#312': 'Handy Gear',
    'skit#315': 'Mutual Trust',
    'skit#317': 'Unique Nature',
    'skit#319': 'Mutual',
}

T.update(fixes)

with open('lotes_p68/SKIT-01.tsv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter='\t')
    fieldnames = reader.fieldnames
    rows = list(reader)

for r in rows:
    r['traducao'] = T[r['id']]

out_p = 'lotes_p68/SKIT-01_retorno.tsv'
with open(out_p, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
    w.writeheader()
    w.writerows(rows)
print("Updated SKIT-01_retorno.tsv")

import csv

translations = {
    # === qev05_010.scr — Leon mocks Judas's mask; tension at dinner ===
    "qev05_010.scr:0": "......Hmph.",
    "qev05_010.scr:1": "What's so funny?",
    "qev05_010.scr:2": "Nothing......\nI just didn't know you wore that\nridiculous mask even while eating.",
    "qev05_010.scr:3": "You must have quite the shameful\npast to hide.",
    "qev05_010.scr:4": "Hey, Leon!",
    "qev05_010.scr:5": "Hmph......\nI don't need lectures from someone\nwho wears a mask over his heart.",
    "qev05_010.scr:6": "What did you say......",
    "qev05_010.scr:7": "N-Now, now, you two!",
    "qev05_010.scr:8": "Um......Leon?\nI'm sorry, Judas is\nalways like this......",
    "qev05_010.scr:9": "Kyle.\nDon't say anything unnecessary.",
    "qev05_010.scr:10": "But......",
    "qev05_010.scr:11": "Hmph, how unpleasant.",
    "qev05_010.scr:12": "Let's go, Rutee.",
    "qev05_010.scr:13": "W-Wait......",
    "qev05_010.scr:14": "Really, I'm so sorry.\nHe's always cold and has no manners.\nPlease forgive him.",
    "qev05_010.scr:15": "............",
    "qev05_010.scr:16": "Judas, ......are you okay?",
    "qev05_010.scr:17": "Hmph, do you really think I'd take\nsuch drivel to heart?",
    "qev05_010.scr:18": "............",
    "qev05_010.scr:19": "......Hey, \u25cb\u25cb.\nWhat are you looking at?",
    "qev05_010.scr:20": "............",
    "qev05_010.scr:21": "............",
    "qev05_010.scr:22": "Hmph.",
    "qev05_010.scr:23": "Huh?\nHey, Judas?\nYou're not going to eat?",
    "qev05_010.scr:24": "Sorry, \u25cb\u25cb.\nI gotta go.",
    "qev05_010.scr:25": "Judas, wait up!!",
    "qev05_010.scr:26": "Quest 'A Closed Heart, An Open\nFuture' has been registered.\nYou can accept it from Judas.",

    # === qev05_020.scr — Judas recruits the player ===
    "qev05_020.scr:0": "I was waiting for you.",
    "qev05_020.scr:1": "Borrowing your help is not ideal,\nbut having a neutral party along\nwill prevent complications later.",
    "qev05_020.scr:2": "............",
    "qev05_020.scr:3": "And let me be clear:\nthis stays between us.",
    "qev05_020.scr:4": "If you so much as breathe a word\nto anyone...... You understand?",
    "qev05_020.scr:5": "............",
    "qev05_020.scr:6": "......That's all.\nLet's go.",

    # === qev05_030.scr — Arriving at the secluded spot ===
    "qev05_030.scr:0": "Hmph......\nSo he figured no one would see him\nout here. Honestly......",
    "qev05_030.scr:1": "......?",
    "qev05_030.scr:2": "No......it's nothing.\nLet's keep moving.",

    # === qev05_040.scr — Judas confides about Leon ===
    "qev05_040.scr:0": "............",
    "qev05_040.scr:1": "What?\nYou look like you want to say something.",
    "qev05_040.scr:2": "............",
    "qev05_040.scr:3": "............",
    "qev05_040.scr:4": "You can't cooperate without\nknowing the circumstances, is that it?",
    "qev05_040.scr:5": "Hmph......\nFine, have it your way.",
    "qev05_040.scr:6": "Just as Kyle sees his parents\nin this world's Stahn and Rutee,\nI see someone in that man.",
    "qev05_040.scr:7": "............",
    "qev05_040.scr:8": "He's a different person, obviously.\nBut......watching his behavior\njust gets under my skin.",
    "qev05_040.scr:9": "I wanted to talk to him somewhere\nwithout any interruptions.",
    "qev05_040.scr:10": "It seems the feeling is mutual--\nhe's been aware of me as well.",
    "qev05_040.scr:11": "......?",
    "qev05_040.scr:12": "I'm not obligated to tell you more.",
    "qev05_040.scr:13": "Don't go prying out of idle sympathy.\nToo much goodwill can destroy you\nin the end.",
    "qev05_040.scr:14": "............",

    # === qev05_050.scr — After the duel with Leon ===
    "qev05_050.scr:0": "Kh......",
    "qev05_050.scr:1": "The match is settled.\nNow answer my questions.",
    "qev05_050.scr:2": "As if......I'd ever......tell you...",
    "qev05_050.scr:3": "............",
    "qev05_050.scr:4": "......I see.\nYou're not one to reason with.",
    "qev05_050.scr:5": "Too consumed by personal matters\nto spare a thought for others.",
    "qev05_050.scr:6": "......!\nWhat are you getting at!?",
    "qev05_050.scr:7": "Exactly what I said.",
    "qev05_050.scr:8": "............Hmph.\nWhat could you know about me?\nDon't speak......as if you do!",
    "qev05_050.scr:9": "......Leon Magnus.",
    "qev05_050.scr:10": "You have far more than you\nrealize.\nDon't forget that.",
    "qev05_050.scr:11": "......?",
    "qev05_050.scr:12": "You......what do you......",
    "qev05_050.scr:13": "Ugh, cough, cough......",
    "qev05_050.scr:14": "\u25cb\u25cb, let's go.",
    "qev05_050.scr:15": "............",
    "qev05_050.scr:16": "Leave him be.\nHis life's not in danger.\nBesides......",
    "qev05_050.scr:17": "The rest is his own affair.",

    # === qev05_060.scr — Judas tells player to forget everything ===
    "qev05_060.scr:0": "Forget it.",
    "qev05_060.scr:1": "???",
    "qev05_060.scr:2": "Everything you saw and heard today.\nForget all of it.",
    "qev05_060.scr:3": "............",
    "qev05_060.scr:4": "You truly don't know the meaning\nof restraint, do you?",
    "qev05_060.scr:5": "......In that way, you're just like\na certain fool I know.",
    "qev05_060.scr:6": "In any case,\ntoday's events stay between us.\n......Understood?",

    # === qev05_070.scr — Pre-battle: Judas confronts Leon about the carrier pigeons ===
    "qev05_070.scr:0": "......I'm counting on you.",
    "qev05_070.scr:1": "............",
    "qev05_070.scr:2": "......?",
    "qev05_070.scr:3": "......Who's there!?",
    "qev05_070.scr:4": "You......\nWhy are you here?",
    "qev05_070.scr:5": "That's my line.\nWhy are you sending pigeons here?",
    "qev05_070.scr:6": "I don't have to answer that.",
    "qev05_070.scr:7": "Heh.\nCorresponding with someone you can't\nlet others know about, then?",
    "qev05_070.scr:8": "......I don't follow.",
    "qev05_070.scr:9": "You've exchanged letters with this\nperson multiple times.",
    "qev05_070.scr:10": "Sometimes even sending flowers and\ntea leaves. I've already confirmed it.",
    "qev05_070.scr:11": "......!",
    "qev05_070.scr:12": "......Even so, how is it your concern?",
    "qev05_070.scr:13": "Hmph......\nI'd rather not be stabbed in my sleep.",
    "qev05_070.scr:14": "If you've nothing to hide,\njust say so.\nWell?",
    "qev05_070.scr:15": "I already told you.\nI don't have to answer.",
    "qev05_070.scr:16": "......If you insult me further,\nyou will regret it.",
    "qev05_070.scr:17": "Oh?\nInteresting.\nThen I'll extract the answer by force.",
    "qev05_070.scr:18": "It can't be helped.\nIt seems that's what he wants.",
    "qev05_070.scr:19": "Ready yourself, \u25cb\u25cb.\nHere he comes!",

    # === qev05_080.scr — Post-battle ===
    "qev05_080.scr:0": "You never learn......\nNo matter what, it ends the same.",
    "qev05_080.scr:1": "That remains to be seen.",
    "qev05_080.scr:2": "The future is not set in stone.\nI'll prove it to you right now!",
    "qev05_080.scr:3": "Let's go, \u25cb\u25cb!",
}

in_file = "lotes/QEV-05.tsv"
out_file = "lotes/QEV-05_retorno.tsv"

with open(in_file, "r", encoding="utf-8") as f:
    reader = csv.reader(f, delimiter="\t")
    header = next(reader)
    rows = list(reader)

out_rows = []
errors = []

for r in rows:
    line_id = r[0]
    orig = r[7]
    orig_lines = orig.split("\\n")
    
    if line_id not in translations:
        errors.append(f"Missing translation for {line_id}")
        continue
    
    trans = translations[line_id]
    trans_lines = trans.split("\n")
    
    if len(orig_lines) != len(trans_lines):
        errors.append(f"Line count mismatch in {line_id}: orig has {len(orig_lines)}, trans has {len(trans_lines)}")
        print(f"Orig: {orig_lines}")
        print(f"Trans: {trans_lines}")
    
    for idx, l in enumerate(trans_lines):
        if len(l) > 42:
            errors.append(f"Line too long in {line_id} line {idx+1}: {len(l)} chars: '{l}'")
    
    if len(trans_lines) > 3:
        errors.append(f"Too many lines in {line_id}: {len(trans_lines)} > 3")
    
    new_row = list(r)
    new_row[8] = trans.replace('\n', '\\n')
    out_rows.append(new_row)

if errors:
    print(f"ERRORS FOUND ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
else:
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(out_rows)
    print(f"Successfully generated {out_file} with {len(out_rows)} rows.")

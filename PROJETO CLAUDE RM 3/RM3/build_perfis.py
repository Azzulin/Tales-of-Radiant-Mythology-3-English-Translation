import csv
from perfil_data_1 import DATA_1
from perfil_data_2 import DATA_2

ALL_DATA = {}
ALL_DATA.update(DATA_1)
ALL_DATA.update(DATA_2)

def wrap_to_k_lines(text, k):
    words = text.split()
    if k <= 1:
        return [' '.join(words)]
    if len(words) < k:
        return words + [''] * (k - len(words))
    
    total_len = len(text)
    target = total_len / k
    
    lines = []
    idx = 0
    lines_remaining = k
    
    while lines_remaining > 0:
        if lines_remaining == 1:
            lines.append(' '.join(words[idx:]))
            break
        
        max_idx = len(words) - (lines_remaining - 1)
        curr_words = [words[idx]]
        idx += 1
        
        while idx < max_idx:
            curr_str = ' '.join(curr_words)
            next_str = ' '.join(curr_words + [words[idx]])
            
            if abs(len(next_str) - target) < abs(len(curr_str) - target):
                curr_words.append(words[idx])
                idx += 1
            elif len(curr_str) < target * 0.75:
                curr_words.append(words[idx])
                idx += 1
            else:
                break
        
        lines.append(' '.join(curr_words))
        lines_remaining -= 1
        
    return lines

def process_file(in_path, out_path, header_tag, prose_idx):
    with open(in_path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    
    fieldnames = list(rows[0].keys())
    
    for i, r in enumerate(rows):
        orig = r['original']
        nl = orig.count('\n')
        body_k = nl - 1
        prose = ALL_DATA[i][prose_idx]
        wrapped = wrap_to_k_lines(prose, body_k)
        full_text = f"[{header_tag}]\n\n" + "\n".join(wrapped)
        
        r['traducao'] = full_text
        r['nota_do_tradutor'] = 'Profile translation aligned with original game lore and RM3 context.'
    
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Wrote {out_path} ({len(rows)} rows)")

process_file('lotes_bancos/PERFIL-ORG.tsv', 'lotes_bancos/PERFIL-ORG_retorno.tsv', 'Original Profile', 0)
process_file('lotes_bancos/PERFIL-TOW3.tsv', 'lotes_bancos/PERFIL-TOW3_retorno.tsv', 'Mythology Profile', 1)

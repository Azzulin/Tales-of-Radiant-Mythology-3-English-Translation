import re, json, os

CAUDA = {
    'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with', 'from',
    'and', 'or', 'but', 'that', 'which', 'who', 'whose', 'as', 'is', 'are',
    'was', 'were', 'be', 'been', 'its', "it's", 'this', 'these', 'those',
    'into', 'onto', 'over', 'under', 'than', 'then', 'when', 'while', 'has',
    'have', 'had', 'can', 'will', 'said', 'made', 'used', 'very', 'more',
    'most', 'such', 'so', 'it', 'his', 'her', 'their', 'one', 'also', 'both',
}
COMUM = {w.capitalize() for w in CAUDA} | {
    'Weapon', 'Recipe', 'Arte', 'Arcane', 'Secret', 'Mystic', 'Spell', 'Can',
    'Contains', 'Commonly', 'Restores', 'Revives', 'Cures', 'Holds', 'Seals',
}

def nomes_proprios(t):
    return {w for w in re.findall(r'\b[A-Z][A-Za-z]{1,}\b', t) if w not in COMUM}

def validate_dict(in_json_path, out_dict):
    d = json.load(open(in_json_path, encoding='utf-8'))
    orig = {x['id']: x for x in d['itens']}
    meta = d['meta_bytes_a_cortar']
    
    erros = []
    cortado = 0
    for k, novo in out_dict.items():
        x = orig.get(k)
        if x is None:
            erros.append((k, 'id nao existe no lote de origem'))
            continue
        try:
            b = novo.encode('ascii')
        except UnicodeEncodeError as e:
            erros.append((k, f'nao e ASCII: {e.object[e.start:e.end]!r}'))
            continue
        velho = x['en']
        if len(b) >= len(velho.encode('ascii', 'replace')):
            erros.append((k, 'nao encurtou'))
            continue
        cortado += len(velho.encode('ascii', 'replace')) - len(b)

        if len(velho) > 35:
            if novo.rstrip()[-1:] not in '.!?':
                erros.append((k, f'nao termina em pontuacao: ...{novo[-28:]!r}'))
            pal = re.findall(r"[A-Za-z']+", novo)
            if pal and pal[-1].lower() in CAUDA:
                erros.append((k, f'frase decapitada: ...{novo[-34:]!r}'))
        perdidos = nomes_proprios(velho) - nomes_proprios(novo)
        if perdidos:
            erros.append((k, f'nome proprio sumiu: {", ".join(sorted(perdidos))}'))

    faltou = meta - cortado
    print(f"Items modified: {len(out_dict)} / {len(orig)}")
    print(f"Bytes cut: {cortado} / Meta: {meta} ({'OK' if faltou <= 0 else f'FALTAM {faltou} B'})")
    print(f"Problems: {len(erros)}")
    for e in erros[:15]:
        print(" ", e)
    return len(erros) == 0 and faltou <= 0

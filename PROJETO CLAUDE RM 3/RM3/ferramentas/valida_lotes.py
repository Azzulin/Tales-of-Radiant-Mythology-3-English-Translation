#!/usr/bin/env python3
"""Coerencia ENTRE lotes. Ver P-50.

Uso: valida_lotes.py <dir_lotes> [elenco_falantes.csv]

`valida_retorno.py` checa um lote contra si mesmo. Esta ferramenta checa TODOS os
retornos juntos — que e' onde a incoerencia de verdade mora: a mesma fala
traduzida de dois jeitos em capitulos diferentes, ou um nome que muda de grafia
no meio da historia.

Checa:
  X1  mesma origem -> mesma traducao, em TODOS os lotes
  X2  nome do indice: quando a origem cita, a traducao usa a grafia adotada
  X3  grafias concorrentes de um mesmo nome proprio (Ad Libitum vs Ad-Libitum)
  X4  o marcador ○○ sobrevive em toda linha que o tem
"""
import sys, os, csv, re, collections, glob

MARCA = '○○'


def le_tsv(p):
    L = [l.split('\t') for l in open(p, encoding='utf-8-sig').read().split('\n') if l.strip()]
    cab = L[0]
    return [dict(zip(cab, r)) for r in L[1:]]


def norm(s):
    """Para casar termo que a quebra de linha partiu ao meio."""
    return s.replace('\\n', ' ').replace('  ', ' ')


def main():
    d = sys.argv[1]
    nomes = {}
    if len(sys.argv) > 2:
        for r in csv.DictReader(open(sys.argv[2], encoding='utf-8')):
            if r.get('nome_jp') and r.get('nome_en'):
                nomes[r['nome_jp']] = r['nome_en']

    arqs = sorted(glob.glob(os.path.join(d, '*_retorno.tsv')))
    if not arqs:
        print(f'nenhum *_retorno.tsv em {d}')
        return 1
    todas = []
    for a in arqs:
        rs = le_tsv(a)
        for r in rs:
            r['_lote'] = os.path.basename(a).replace('_retorno.tsv', '')
        todas += rs
    print(f'{len(arqs)} lotes, {len(todas)} falas: ' +
          ', '.join(os.path.basename(a).replace('_retorno.tsv', '') for a in arqs))

    erros = []

    # X1 — mesma origem, mesma traducao, entre lotes
    por = collections.defaultdict(list)
    for r in todas:
        if r.get('original') and r.get('traducao', '').strip():
            por[r['original']].append(r)
    rep = {o: rs for o, rs in por.items() if len({x['traducao'] for x in rs}) > 1}
    print(f'\nX1  origens que aparecem mais de uma vez: '
          f'{sum(1 for rs in por.values() if len(rs) > 1)}')
    if rep:
        erros.append(f'X1: {len(rep)} origens com traducao divergente')
        for o, rs in list(rep.items())[:10]:
            print(f'  ! {o[:52]}')
            for x in rs:
                print(f'      [{x["_lote"]}] {x["traducao"][:56]}')
    else:
        print('    conflitos: 0')

    # X4 — marcador do nome do jogador
    perdidos = [r for r in todas if MARCA in r.get('original', '')
                and MARCA not in r.get('traducao', '')]
    print(f'\nX4  linhas com {MARCA}: '
          f'{sum(1 for r in todas if MARCA in r.get("original", ""))}   '
          f'perdidas: {len(perdidos)}')
    if perdidos:
        erros.append(f'X4: {len(perdidos)} linhas perderam o marcador')
        for r in perdidos[:8]:
            print(f'  ! [{r["_lote"]}] {r["id"]}: {r["traducao"][:56]}')

    # X2 — nome citado, grafia usada
    def katakana(c):
        return bool(c) and ('ァ' <= c <= 'ヶ' or c in 'ー・ｰ')

    def hiragana(c):
        return bool(c) and ('ぁ' <= c <= 'ゖ' or c in 'ー・')

    def kanji(c):
        return bool(c) and '一' <= c <= '鿿'
    faltas = []
    for r in todas:
        t = norm(r.get('traducao', ''))
        for njp, nen in nomes.items():
            if len(njp) < 3 or any(parte in t for parte in nen.split()):
                continue
            eh_katakana = any(katakana(c) for c in njp)
            eh_hiragana = any(hiragana(c) for c in njp)

            def limite(c):
                return ((eh_katakana and katakana(c)) or
                        (eh_hiragana and (hiragana(c) or kanji(c) or katakana(c))))
            for m in re.finditer(re.escape(njp), r.get('original', '')):
                a = r['original'][m.start() - 1] if m.start() else ''
                b = r['original'][m.end()] if m.end() < len(r['original']) else ''
                if limite(a) or limite(b):
                    continue
                faltas.append((r, njp, nen))
                break
    print(f'\nX2  linhas que citam nome do indice sem usar a grafia adotada: {len(faltas)}')
    for r, njp, nen in faltas[:10]:
        print(f'  ? [{r["_lote"]}] {r["id"]}: `{njp}` -> esperado `{nen.split()[0]}`')
        print(f'      {r["traducao"][:64]}')
    if faltas:
        print('    (pode ser anafora legitima — "he", "they" — confira antes de recusar)')

    # X3 — grafias concorrentes
    print('\nX3  grafias concorrentes de nome proprio')
    vistos = collections.Counter()
    for r in todas:
        for w in re.findall(r'[A-Z][a-z]+(?:[ -][A-Z][a-z]+)*', norm(r.get('traducao', ''))):
            vistos[w] += 1
    susp = []
    chaves = list(vistos)
    for i, a in enumerate(chaves):
        for b in chaves[i + 1:]:
            ca, cb = a.replace('-', '').replace(' ', '').lower(), b.replace('-', '').replace(' ', '').lower()
            if ca == cb and a != b:
                susp.append((a, vistos[a], b, vistos[b]))
    if susp:
        erros.append(f'X3: {len(susp)} pares de grafia concorrente')
        for a, na, b, nb in susp[:10]:
            print(f'  ! {a!r} ({na}x)  vs  {b!r} ({nb}x)')
    else:
        print('    nenhuma')

    print()
    if erros:
        print('COERENCIA COMPROMETIDA: ' + ' | '.join(erros))
        return 1
    print('COERENTE — X1, X3 e X4 sem falha (X2 e aviso, nao recusa)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

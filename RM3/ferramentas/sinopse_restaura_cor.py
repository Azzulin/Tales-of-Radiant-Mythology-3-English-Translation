#!/usr/bin/env python3
"""Devolve os codigos de cor aos nomes proprios da sinopse (P-71).

O banco `v2069` destaca nome proprio e termo-chave com um par de codigos:

    \x13 <3 bytes RGB> <texto> \x14

Sao 285 pares sobre 39 termos, em 3 cores (`8080ff` azul, `adff2f` verde,
`fd6aff` rosa). O extrator original decodificou esses bytes como texto e o lote
saiu com `\ufffd` no lugar — **o tradutor nunca os viu**, e as 271 linhas
afetadas voltaram sem destaque nenhum.

Esta ferramenta reconstitui: para cada linha, ve quais termos estavam
destacados no japones, acha o equivalente ingles na traducao (pelo mapa de
termos ja aprovados em outros lotes) e envolve com o mesmo codigo e a mesma cor.

Nao adivinha: termo cujo equivalente nao aparece na traducao fica sem destaque,
e e' relatado. Perder a cor e' perder enfase visual; inventar posicao seria
pior.

Uso:
  sinopse_restaura_cor.py <iso> <lba> <lotes_glob> <saida.tsv> [--mapa CSV]
"""
import sys, os, csv, re, glob, collections, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
import oldata

SEC = 2048
V_SINOPSE = 2069
ABRE = 0x13
FECHA = 0x14
RX = re.compile(rb'\x13(...)(.*?)\x14', re.S)


def mapa_termos(raiz):
    """japones -> ingles, a partir de tudo que ja tem traducao aprovada."""
    m = collections.defaultdict(collections.Counter)
    padroes = [os.path.join(raiz, 'lotes', '*_retorno.tsv'),
               os.path.join(raiz, 'lotes_p68', '*_retorno.tsv'),
               os.path.join(raiz, 'lotes_bancos', '*_retorno.tsv')]
    for pat in padroes:
        for p in glob.glob(pat):
            for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
                o = (r.get('original') or '').strip()
                t = (r.get('traducao') or '').strip()
                if o and t:
                    m[o][t] += 1
    for p in glob.glob(os.path.join(raiz, 'dados', '*.csv')):
        try:
            rs = list(csv.DictReader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if not rs or 'original' not in rs[0]:
            continue
        for r in rs:
            o = (r.get('original') or '').strip()
            t = (r.get('traducao') or '').strip()
            if o and t and t != '(verbatim)':
                m[o][t] += 1
    return {k: [t for t, _ in v.most_common()] for k, v in m.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('lba', type=int)
    ap.add_argument('lotes_glob')
    ap.add_argument('saida')
    ap.add_argument('--raiz', default='.')
    args = ap.parse_args()

    with open(args.iso, 'rb') as f:
        _, c, entries, _ = load_index(f, args.lba * SEC)
        e = {x['v']: x for x in entries}[V_SINOPSE]
        f.seek(args.lba * SEC + e['off'])
        raw = f.read(e['span'])
    nar = oldata.parse(raw)['narracao']

    # por indice de linha: [(cor, termo_jp)]
    destaque = {}
    for i, l in enumerate(nar):
        ms = list(RX.finditer(l))
        if ms:
            destaque[i] = [(m.group(1), m.group(2)) for m in ms]
    print(f'{len(destaque)} linhas com destaque, '
          f'{sum(len(v) for v in destaque.values())} pares')

    termos = mapa_termos(args.raiz)
    rows = []
    for p in sorted(glob.glob(args.lotes_glob)):
        rows += list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
    # casa por TEXTO, nao por indice: a narracao tem 1.156 linhas e o lote
    # 1.125 (o extrator filtrou vazias), entao `ordem` nao alinha com a
    # posicao real. A chave e' o japones sem os codigos, que e' o que o
    # lote guarda.
    def limpo(b):
        # MESMA decodificacao que o extrator usou: os bytes de codigo viram
        # �, e e' assim que o japones esta guardado no lote. Remover os
        # codigos aqui geraria uma chave que nao existe do outro lado.
        return b.decode('euc_jp', 'replace')

    porjp = {}
    for r in rows:
        porjp.setdefault(r['original'], r)

    rest = falha = 0
    naoachou = collections.Counter()
    for i, pares in destaque.items():
        r = porjp.get(limpo(nar[i]))
        if not r or not r.get('traducao'):
            falha += len(pares)
            naoachou['(linha nao casou)'] += len(pares)
            continue
        t = r['traducao']
        for cor, jp in pares:
            try:
                jps = jp.decode('euc_jp')
            except Exception:
                continue
            # tenta cada variante ja aprovada, da mais LONGA para a mais curta:
            # `Star Crystal` antes de `Crystal`, senao o destaque pega so metade
            cands = sorted(termos.get(jps, []), key=len, reverse=True)
            achou = None
            for en in cands:
                if en and en in t:
                    achou = en
                    break
            if achou is None:                    # tenta sem diferenciar caixa
                baixo = t.lower()
                for en in cands:
                    if en and en.lower() in baixo:
                        k = baixo.index(en.lower())
                        achou = t[k:k + len(en)]
                        break
            if achou is None:
                falha += 1
                naoachou[jps] += 1
                continue
            marc = ('' + cor.decode('latin1')) + achou + ''
            t = t.replace(achou, marc, 1)
            rest += 1
        r['traducao'] = t

    print(f'destaques restaurados: {rest}')
    print(f'nao restaurados: {falha}')
    if naoachou:
        print('  termos cujo equivalente nao aparece na traducao:')
        for k, n in naoachou.most_common(12):
            print(f'    {n:>3}x  {k}  -> {termos.get(k, "(sem traducao)")!r}')

    if rows:
        with open(args.saida, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter='\t')
            w.writeheader()
            w.writerows(rows)
        print(f'-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

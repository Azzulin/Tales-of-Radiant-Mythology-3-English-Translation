#!/usr/bin/env python3
"""Auditoria de largura do texto do EBOOT: o ingles cabe na coluna? (P-93)

Os menus do RM3 desenham cada campo numa coluna de largura fixa, dimensionada
pelo japones mais largo daquela lista (`格闘家` ao lado de `狩人`, nome do titulo
ao lado da condicao). O ingles mais largo invade a coluna vizinha (`Martial
Artist` por cima de `Hunter`, en29/en30).

Largura em PIXELS, com os avancos reais da fonte que o jogo usa
(`jpn0.pgf`, `pgf_largura.py`): ASCII e' proporcional, um `i` mede 4,25 px e
um `M` 18 px, como um ideograma.

**Coluna** = o mesmo campo da mesma tabela de ponteiros:
  - banco de item/equipamento: `(va_ponteiro - base) % stride` do registro
    (`dados/item_equip_registros.csv`, P-67.7);
  - demais blocos: o stride do registro e' detectado pelos proprios ponteiros
    (o menor S, multiplo de 4, para o qual a maioria dos ponteiros p tem
    tambem p+S no bloco); campo = `(p - p_min) % S`. Numa lista simples
    (S = 4) o campo e' um so', e a lista e' partida em trechos de tipo parecido
    (uma linha / varias linhas), porque um mesmo array mistura rotulo e
    descricao.
Orcamento da coluna = a maior largura japonesa (por linha) do campo.

Classes, da mais grave para a mais branda:
  ESTOURA      ingles mais largo que o orcamento da coluna
  PROPRIA      cabe na coluna, mas e' mais largo que o proprio japones, num
               campo curto (orcamento <= 180 px): candidato a encostar no vizinho
So' le. Escreve o CSV pedido.

Uso:
  largura_auditoria.py <jpn0.pgf> --lotes <csv...> [--csv saida.csv] [--folga 0.03]
"""
import sys, os, csv, re, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgf_largura import Fonte

CURTO = 180.0
LF = chr(10)
TOKEN_LF = chr(92) + 'n'
KANA = re.compile('[ァ-ヶー・０-９Ａ-Ｚ　]+')


def linhas(t):
    t = t.replace('\\n', '\n').replace('\\t', '')
    return [x for x in re.split('[\n#]', t)]


def stride_de(ps):
    s = set(ps)
    if len(ps) < 3:
        return 4
    for S in range(4, 260, 4):
        if sum(1 for p in ps if p + S in s) >= 0.5 * len(ps):
            return S
    return 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pgf')
    ap.add_argument('--lotes', nargs='+', required=True)
    ap.add_argument('--csv')
    ap.add_argument('--folga', type=float, default=0.03)
    ap.add_argument('--registros', default='dados/item_equip_registros.csv')
    a = ap.parse_args()
    F = Fonte(a.pgf)

    def larg(t):
        return max(F.largura(x) for x in linhas(t)) if t else 0.0

    reg = {}
    if os.path.exists(a.registros):
        for r in csv.DictReader(open(a.registros, encoding='utf-8')):
            if r['stride_bytes'].isdigit():
                reg[r['categoria_en']] = (int(r['va_registro_base'], 16), int(r['stride_bytes']))

    rows = []
    for L in a.lotes:
        for r in csv.DictReader(open(L, encoding='utf-8')):
            t = r.get('traducao') or ''
            if t in ('', '(verbatim)') or not r.get('original'):
                continue
            r['_lote'] = os.path.basename(L)
            r['_base'] = (r.get('bloco') or 'criacao').split('__')[0]
            r['_vp'] = int(r['va_ponteiro'], 16)
            rows.append(r)

    # campo de cada linha
    por_base = collections.defaultdict(list)
    for r in rows:
        por_base[(r['_lote'], r['_base'])].append(r)
    for (lote, base), rs in por_base.items():
        if base in reg:
            b0, S = reg[base]
            nomes = collections.defaultdict(set)
            for r in rs:
                r['_campo'] = '%s+%d' % (base, (r['_vp'] - b0) % S)
                if (r['_vp'] - b0) % S == 0:
                    nomes[(r['_vp'] - b0) // S].add(r['traducao'])
            for r in rs:
                # campo de leitura (katakana do nome, usado para ordenar): o
                # tradutor repetiu o ingles do nome nele; nao e' desenhado
                if ((r['_vp'] - b0) % S and KANA.fullmatch(r['original'])
                        and r['traducao'] in nomes[(r['_vp'] - b0) // S]):
                    r['_campo'] = None
            continue
        # registro = trecho de ponteiros contiguos (gap 4); o proximo registro
        # comeca depois de um gap maior (campos nao-ponteiro no meio). Titulo:
        # nome/descricao/condicao/efeito em +0/+4/+8/+C, stride 48 (P-93)
        ps = sorted({r['_vp'] for r in rs})
        regs, cur = [], [ps[0]]
        for p in ps[1:]:
            if p - cur[-1] == 4:
                cur.append(p)
            else:
                regs.append(cur)
                cur = [p]
        regs.append(cur)
        # registro curto (<= 8 ponteiros): coluna = (tamanho, posicao). Trecho
        # longo e' uma LISTA (um array de 309 ponteiros nao tem 309 colunas):
        # parte em trechos contiguos do mesmo tipo (uma/varias linhas, curto/longo)
        por_vp = collections.defaultdict(list)
        for r in rs:
            por_vp[r['_vp']].append(r)
        for ri, x in enumerate(regs):
            if len(x) <= 8:
                for i, p in enumerate(x):
                    for r in por_vp[p]:
                        r['_campo'] = '%s+r%d.%d' % (base, len(x), i)
                continue
            k, ant = 0, None
            for p in x:
                o = por_vp[p][0]['original']
                tipo = ('n' if TOKEN_LF in o or LF in o else '1', larg(o) > CURTO)
                if ant is not None and tipo != ant:
                    k += 1
                ant = tipo
                for r in por_vp[p]:
                    r['_campo'] = '%s#L%d.%d' % (base, ri, k)

    rows = [r for r in rows if r.get('_campo')]
    orc = collections.defaultdict(float)
    for r in rows:
        r['_wjp'] = larg(r['original'])
        r['_wen'] = larg(r['traducao'])
        orc[(r['_lote'], r['_campo'])] = max(orc[(r['_lote'], r['_campo'])], r['_wjp'])

    out, vistos = [], set()
    for r in rows:
        o = orc[(r['_lote'], r['_campo'])]
        chave = (r['_lote'], r['_campo'], r['traducao'])
        if chave in vistos:
            continue
        vistos.add(chave)
        if r['_wen'] > o * (1 + a.folga):
            cl = 'ESTOURA'
        elif o <= CURTO and r['_wen'] > r['_wjp'] * (1 + a.folga):
            cl = 'PROPRIA'
        else:
            continue
        out.append({'classe': cl, 'lote': r['_lote'], 'campo': r['_campo'], 'id': r.get('id', ''),
                    'va_ponteiro': r['va_ponteiro'], 'original': r['original'],
                    'traducao': r['traducao'], 'px_jp': '%.0f' % r['_wjp'],
                    'px_en': '%.0f' % r['_wen'], 'px_coluna': '%.0f' % o,
                    'excesso_px': '%.0f' % (r['_wen'] - o)})
    out.sort(key=lambda x: (x['classe'] != 'ESTOURA', -float(x['excesso_px'])))
    c = collections.Counter(x['classe'] for x in out)
    print('%d strings traduzidas medidas (%d colunas)' % (len(rows), len(orc)))
    print('  ESTOURA a coluna: %d   | mais largo que o proprio japones (campo curto): %d'
          % (c['ESTOURA'], c['PROPRIA']))
    porl = collections.Counter((x['lote'], x['campo'].split('+')[0].split('#')[0]) for x in out if x['classe'] == 'ESTOURA')
    for (l, b), n in porl.most_common(25):
        print('   %-34s %-22s %d' % (l, b, n))
    if a.csv:
        with open(a.csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ['classe'])
            w.writeheader()
            w.writerows(out)
        print('-> %s' % a.csv)
    return 0


if __name__ == '__main__':
    sys.exit(main())

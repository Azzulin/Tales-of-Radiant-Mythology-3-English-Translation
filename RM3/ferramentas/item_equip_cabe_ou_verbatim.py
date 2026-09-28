#!/usr/bin/env python3
"""Quando o texto EN de um bloco nao cabe na arena, devolve ao japones as
strings estritamente necessarias — e nenhuma a mais (P-67.14).

Por que `(verbatim)` e nao "tirar do lote": tirar a linha faria o ponteiro dela
virar um ponteiro DE FORA apontando para DENTRO da arena, e a guarda 2 recusaria
o build — com razao, porque o pool seria escrito por cima do japones que esse
ponteiro ainda le. `(verbatim)` e' o mecanismo que o `eboot_build2.py` ja' tem:
copia os `bytes_jp` originais para dentro do pool e reescreve o ponteiro. A
string continua em japones, mas viaja junto e nada aponta para lugar nenhum.

Escolha de quem volta: as de MAIOR economia (`len(en) - bytes_jp`) primeiro, que
e' o que devolve o maximo de bytes por string sacrificada — assim o numero de
strings que ficam em japones e' o menor possivel. Por padrao so' mexe em
descricao (> --min-bytes), nunca em nome de item, que e' o que o jogador mais ve.

Uso:
  item_equip_cabe_ou_verbatim.py <csv...> --ponteiros <csv...> [--bloco B]
                                 [--min-bytes 36] [--aplicar]
"""
import sys, os, csv, argparse, collections, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from item_equip_segmenta_arena import segmentos_livres


def le(p):
    with open(p, encoding='utf-8') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--ponteiros', nargs='+', required=True)
    ap.add_argument('--bloco', action='append',
                    help='so estes blocos (padrao: todos que estouram)')
    ap.add_argument('--min-bytes', type=int, default=36,
                    help='so devolve string maior que isto (padrao 36: poupa nome de item)')
    ap.add_argument('--preservar', action='append', default=[],
                    help='CSV cujas strings NUNCA voltam ao japones — use para todo '
                         'lote ja em producao (P-53: nao desfazer o que ja esta em jogo)')
    ap.add_argument('--eboot', default='eboot/EBOOT_dec_LIMPO.bin',
                    help='mesmo criterio do segmentador: sem ele o espaco e '
                         'superestimado e o build estoura depois (P-77)')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    raw = None
    if args.eboot and os.path.exists(args.eboot):
        raw = open(args.eboot, 'rb').read()

    ptrs = set()
    for p in args.ponteiros:
        for r in le(p)[1]:
            ptrs.add(int(r['va_ponteiro'], 16))

    intocaveis = set()
    for p in args.preservar:
        for r in le(p)[1]:
            intocaveis.add(int(r['va_string'], 16))
    if intocaveis:
        print(f'{len(intocaveis)} strings marcadas como intocaveis (ja em producao)\n')

    arqs = {p: le(p) for p in args.csvs}
    todas = [r for p in args.csvs for r in arqs[p][1]]
    pai = collections.OrderedDict()
    for r in todas:
        pai.setdefault(re.sub(r'__s\d+$', '', r['bloco']), []).append(r)

    total_verb = 0
    for nome, rs in pai.items():
        if args.bloco and nome not in args.bloco:
            continue
        strs = {(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs}
        ini = min(v for v, _ in strs)
        fim = max(v + b + 1 for v, b in strs)
        esp = sum(b - a for a, b in segmentos_livres(ini, fim, ptrs, strs, raw))

        # pool por texto distinto (dedup, como o eboot_build2 faz). `(verbatim)`
        # e' chaveado por string: o build copia os `bytes_jp` de CADA uma, entao
        # duas verbatim nao deduplicam entre si.
        porTexto = collections.OrderedDict()
        for r in rs:
            chave = (('V', r['va_string']) if r['traducao'] == '(verbatim)'
                     else r['traducao'])
            porTexto.setdefault(chave, []).append(r)

        def custo(t, linhas):
            if isinstance(t, tuple):
                return int(linhas[0]['bytes_jp']) + 1
            return len(t.replace('\\n', '\n').encode('ascii', 'replace')) + 1

        pool = sum(custo(t, l) for t, l in porTexto.items())
        if pool <= esp:
            continue

        falta = pool - esp
        # candidatas: economia por string devolvida, maior primeiro
        cands = []
        for t, linhas in porTexto.items():
            if isinstance(t, tuple):        # ja esta em japones
                continue
            en = len(t.replace('\\n', '\n').encode('ascii', 'replace'))
            jp = int(linhas[0]['bytes_jp'])
            if en <= args.min_bytes:
                continue
            if any(int(r['va_string'], 16) in intocaveis for r in linhas):
                continue                       # ja esta em jogo: nao retrocede
            if en - jp > 0:
                cands.append((en - jp, t, linhas))
        cands.sort(key=lambda x: -x[0])

        devolvidas, ganho = [], 0
        for g, t, linhas in cands:
            if ganho >= falta:
                break
            ganho += g
            devolvidas.append((t, linhas))

        print(f'[{nome}] espaco {esp} B, pool {pool} B, faltam {falta} B')
        if ganho < falta:
            print(f'  AVISO: mesmo devolvendo todas as {len(cands)} candidatas '
                  f'(> {args.min_bytes} B) so da {ganho} B — ainda faltam {falta-ganho} B')
        print(f'  -> {len(devolvidas)} strings voltam ao japones, devolvendo {ganho} B '
              f'({100.0*len(devolvidas)/len(porTexto):.1f}% das {len(porTexto)} distintas)')
        for t, linhas in devolvidas:
            for r in linhas:
                r['traducao'] = '(verbatim)'
        total_verb += len(devolvidas)

    print(f'\ntotal devolvido ao japones: {total_verb} strings distintas')
    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    for p in args.csvs:
        cols, rows = arqs[p]
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f'-> {p}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

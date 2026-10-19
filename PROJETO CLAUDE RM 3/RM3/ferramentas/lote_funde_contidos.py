#!/usr/bin/env python3
"""Funde num bloco hospedeiro todo bloco cuja arena cai DENTRO da dele (P-72).

O `eboot_build2.py` exige uma arena por bloco e recusa quando duas se cruzam —
com razao: cada bloco reempacota a sua, e a que estiver por baixo vira lixo.
Quando uma frente NOVA e' mais larga que uma antiga e a engole (o bloco `ui` do
P-68 cobre `guia_botoes`, `loja_avisos`, `nomes_cidade`, ...), a saida e' a
mesma do P-62.1 e do P-67.11: **um bloco so'**.

As linhas do bloco contido passam para o hospedeiro com a traducao intacta —
elas ja' estao em jogo, e nada aqui as reescreve (P-53).

Usa `arena_ini`/`arena_fim` quando o lote os declara (blocos segmentados do
P-67.12); senao deriva de min..max das strings, como o build faz.

Uso:
  lote_funde_contidos.py <csv...> [--aplicar]
"""
import sys, csv, argparse, collections


def le(p):
    with open(p, encoding='utf-8') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    arqs = {p: le(p) for p in args.csvs}
    por = collections.defaultdict(list)
    onde = {}
    for p in args.csvs:
        for r in arqs[p][1]:
            b = (r.get('bloco') or 'criacao') or 'criacao'
            por[b].append(r)
            onde.setdefault(b, p)

    arena = {}
    for b, rs in por.items():
        if rs[0].get('arena_ini') and rs[0].get('arena_fim'):
            arena[b] = (int(rs[0]['arena_ini'], 16), int(rs[0]['arena_fim'], 16))
        else:
            vs = [(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs]
            arena[b] = (min(v for v, _ in vs), max(v + n + 1 for v, n in vs))

    # contido = arena inteiramente dentro da de outro, e o outro e' MAIOR
    plano = []
    for b, (a, f) in arena.items():
        for h, (a2, f2) in arena.items():
            if h == b or (f2 - a2) <= (f - a):
                continue
            if a2 <= a and f <= f2:
                plano.append((b, h))
                break

    if not plano:
        print('nenhum bloco contido em outro — nada a fundir')
        return 0
    print(f'{len(plano)} blocos a fundir:')
    for b, h in plano:
        print(f'   {b:<22} ({len(por[b]):>4} linhas, {onde[b]:<34}) -> {h}')

    for b, h in plano:
        for r in por[b]:
            r['bloco'] = h
            # o hospedeiro pode ter arena explicita; o contido passa a segui-la
            if 'arena_ini' in r:
                r['arena_ini'] = por[h][0].get('arena_ini', '')
                r['arena_fim'] = por[h][0].get('arena_fim', '')

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

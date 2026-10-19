#!/usr/bin/env python3
"""Traz para o lote os ponteiros que apontam para string VAZIA dentro de uma
arena (P-77).

Sobra deste tipo, depois de a arena ser picada em volta de todo dado alheio:
entre duas strings do lote quase sempre ha' um ou dois NUL de alinhamento, e
ha' ponteiros no jogo que usam justamente esse NUL como "texto vazio" — um
campo de registro que nao tem nada escrito. `segmentos_livres` nao consegue
separa-los: sao zero byte, nao sao "dado", e ficam colados nas strings do lote.

`lote_extras_gera.py` tambem nao os pega, porque nao ha' string nenhuma ali.
Mas a guarda 2 os ve, e com razao: reempacotar a arena move o NUL de lugar.

A solucao e' a mais simples possivel — entram no lote com traducao vazia. O
pool ganha UM byte nulo (todos deduplicam nele, P-42.3) e todos os ponteiros
passam a apontar para ele. Nada fica lendo endereco velho.

Uso:
  lote_vazias_gera.py <eboot_limpo> <saida.csv> <lote...> [--aplicar]
"""
import sys, csv, struct, argparse, collections

DELTA = 0x08803000
ELF_FIM = 5862704
COLS = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'id',
        'original', 'arena_ini', 'arena_fim']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('saida')
    ap.add_argument('lotes', nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    rows = []
    for p in args.lotes:
        with open(p, encoding='utf-8') as f:
            rows += list(csv.DictReader(f))
    blocos = collections.OrderedDict()
    for r in rows:
        blocos.setdefault(r.get('bloco') or 'criacao', []).append(r)

    arenas = {}
    for b, rs in blocos.items():
        if rs[0].get('arena_ini') and rs[0].get('arena_fim'):
            arenas[b] = (int(rs[0]['arena_ini'], 16), int(rs[0]['arena_fim'], 16))
        else:
            vs = [(int(x['va_string'], 16), int(x['bytes_jp'])) for x in rs]
            arenas[b] = (min(v for v, _ in vs), max(v + n + 1 for v, n in vs))
    do_lote = {int(r['va_string'], 16) for r in rows}

    novas = []
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if w in do_lote or not (DELTA <= w < DELTA + ELF_FIM):
            continue
        if raw[w - DELTA] != 0:                  # nao e' string vazia
            continue
        for b, (a, f) in arenas.items():
            if a <= w < f:
                ai, af = arenas[b]
                novas.append({'bloco': b, 'va_ponteiro': f'0x{q+DELTA:08X}',
                              'va_string': f'0x{w:08X}', 'bytes_jp': '0',
                              'traducao': '', 'id': f'vazia#{len(novas)}',
                              'original': '',
                              'arena_ini': f'0x{ai:08X}', 'arena_fim': f'0x{af:08X}'})
                break

    alvos = collections.Counter(r['va_string'] for r in novas)
    print(f'{len(novas)} ponteiros para string vazia dentro de arena, '
          f'{len(alvos)} alvos distintos')
    for b, c in collections.Counter(r['bloco'] for r in novas).most_common():
        print(f'   [{b}] {c}')

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    with open(args.saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        w.writerows(novas)
    print(f'-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

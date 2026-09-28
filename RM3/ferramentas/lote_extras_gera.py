#!/usr/bin/env python3
"""Gera o `extras` de um lote: as strings que MORAM na arena mas nao sao do lote.

A guarda 2 do `eboot_build2.py` recusa build em que um ponteiro de fora aponte
para dentro de uma arena — o pool seria escrito por cima do que esse ponteiro
ainda le. Quando a frente nova e' uma REGIAO (e nao uma tabela), quase sempre ha
string alheia no meio dela: o extrator pegou so' o que tinha kana, e sobrou
texto ja ASCII, sentinela, ou de outra frente.

A saida e' a mesma que o banco de item/equipamento ja usa (`item_equip_extras`):
essas strings entram no lote como `(verbatim)`, viajam junto no pool e tem o
ponteiro reescrito. Nada fica apontando para fora, e nenhum texto se perde.

Uso:
  lote_extras_gera.py <eboot_dec> <lote.csv> <saida_extras.csv> [--lotes CSV...]
"""
import sys, csv, struct, argparse, collections

DELTA = 0x08803000
ELF_FIM = 5862704


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('lote')
    ap.add_argument('saida')
    ap.add_argument('--lotes', nargs='*', default=[],
                    help='demais lotes do build: suas strings nao viram extras')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()
    rows = list(csv.DictReader(open(args.lote, encoding='utf-8')))
    por = collections.defaultdict(list)
    for r in rows:
        por[r['bloco']].append(r)

    arenas = {}
    for b, rs in por.items():
        vs = [(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs]
        arenas[b] = (min(v for v, _ in vs), max(v + n + 1 for v, n in vs))

    do_lote = {int(r['va_string'], 16) for r in rows}
    for L in args.lotes:
        for r in csv.DictReader(open(L, encoding='utf-8')):
            do_lote.add(int(r['va_string'], 16))

    achados = collections.OrderedDict()
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if w in do_lote:
            continue
        for b, (a, f) in arenas.items():
            if a <= w < f:
                achados.setdefault(w, (b, []))[1].append(q + DELTA)
                break

    linhas = []
    for va, (b, ptrs) in achados.items():
        p = va - DELTA
        fim = raw.find(b'\x00', p, p + 400)
        n = (fim - p) if fim > p else 0
        for vp in ptrs:
            linhas.append({'bloco': b, 'va_ponteiro': f'0x{vp:08X}',
                           'va_string': f'0x{va:08X}', 'bytes_jp': n,
                           'traducao': '(verbatim)',
                           'original': raw[p:p + n].decode('euc_jp', 'replace')})

    c = collections.Counter(l['bloco'] for l in linhas)
    print(f'{len(achados)} strings alheias dentro das arenas, {len(linhas)} ponteiros')
    for b, n in c.most_common():
        print(f'   {b:<16}{n:>6}')
    cols = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'original']
    with open(args.saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(linhas)
    print(f'-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Colhe os termos de UI que o proprio jogo cita entre 「」 no guia (v2065).

Uso: guia_termos.py <iso> <lba> <size> <saida.csv>

Somente leitura. Emite: origem_jp, bytes_jp, ocorrencias, contexto_1
`bytes_jp` = tamanho em bytes na codificacao real do arquivo (EUC-JP, ver P-27).
"""
import sys, csv, struct, collections
from bdi import load_index
from guia import parse

ENC = 'euc_jp'
ABRE = '「'   # 「
FECHA = '」'  # 」


def colher(txt, saco, ctx):
    i = 0
    while True:
        a = txt.find(ABRE, i)
        if a < 0:
            break
        b = txt.find(FECHA, a + 1)
        if b < 0:
            break
        t = txt[a + 1:b]
        if t and ABRE not in t:
            saco[t] += 1
            ctx.setdefault(t, txt.replace('\n', ' ')[:120])
        i = b + 1


def main():
    iso, lba, size, saida = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    base = lba * 2048
    with open(iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        alvo = [e for e in entries if e['v'] == 2065]
        if not alvo:
            print('v2065 ausente', file=sys.stderr)
            return 1
        e = alvo[0]
        f.seek(base + e['off'])
        blob = f.read(e['span'])
    g = parse(blob)
    saco = collections.Counter()
    ctx = {}
    nstr = 0
    for r in g['regs']:
        for campo in ('titulo', 'corpo'):
            b = r[campo]
            if not b:
                continue
            nstr += 1
            colher(b.decode(ENC, 'replace'), saco, ctx)
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['origem_jp', 'bytes_jp', 'ocorrencias', 'contexto_1'])
        for t, n in sorted(saco.items(), key=lambda kv: (-kv[1], -len(kv[0]), kv[0])):
            w.writerow([t, len(t.encode(ENC)), n, ctx.get(t, '')])
    print(f'registros={g["count"]} strings={nstr} termos_distintos={len(saco)} '
          f'ocorrencias={sum(saco.values())}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

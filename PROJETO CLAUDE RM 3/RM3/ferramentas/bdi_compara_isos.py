#!/usr/bin/env python3
"""Compara o `namco.bdi` de duas ISOs ENTRADA POR ENTRADA, cada uma pelo seu
proprio indice (P-84) — e diz o que mudou de uma build para a outra.

Serve para a pergunta que toda ISO nova precisa responder: *o que a anterior
tinha continua aqui?* Com o `namco.bdi` crescido as entradas mudam de setor, entao
comparar por posicao nao serve mais.

Para cada entrada que difere, desce um nivel: se e' EZBIND, lista quais arquivos
internos mudaram; e para cada arquivo (ou entrada gzip) compara o conteudo
DESCOMPRIMIDO, que e' o que o jogo le. Padding de zeros no fim do span e'
ignorado (uma ISO crescida tem mais).

Somente leitura nas duas ISOs.

Uso:
  bdi_compara_isos.py <iso_a> <iso_b> [--lba 106896] [--csv saida.csv]
"""
import sys, os, gzip, zlib, struct, csv, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse

SEC = 2048
GZ = b'\x1f\x8b\x08'


def conteudo(b):
    """Descomprime se for gzip; se nao, devolve sem o padding de zeros."""
    if b[:3] == GZ:
        try:
            return zlib.decompressobj(31).decompress(b)
        except zlib.error:
            pass
    return b.rstrip(b'\x00')


def arquivos(blob):
    pe = ezbind_parse(blob)
    if not pe:
        return None
    _, _, regs = pe
    return {r[0]: conteudo(blob[r[3]:r[3] + r[2]]) for r in regs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_a')
    ap.add_argument('iso_b')
    ap.add_argument('--lba', type=int, default=106896)
    ap.add_argument('--csv')
    a = ap.parse_args()
    base = a.lba * SEC
    fa, fb = open(a.iso_a, 'rb'), open(a.iso_b, 'rb')
    _, ca, ea, _ = load_index(fa, base)
    _, cb, eb, _ = load_index(fb, base)
    if ca != cb:
        print('count diferente: %d x %d — nao sao a mesma estrutura' % (ca, cb))
        return 1

    linhas, iguais = [], 0
    for x, y in zip(ea, eb):
        fa.seek(base + x['off'])
        ba = fa.read(x['span'])
        fb.seek(base + y['off'])
        bb = fb.read(y['span'])
        if ba.rstrip(b'\x00') == bb.rstrip(b'\x00'):
            iguais += 1
            continue
        aa, ab = arquivos(ba), arquivos(bb)
        if aa is None or ab is None:
            if conteudo(ba) == conteudo(bb):
                linhas.append((x['v'], '(entrada)', 'so_compressao'))
            else:
                linhas.append((x['v'], '(entrada)', 'conteudo'))
            continue
        mud = [n for n in sorted(set(aa) | set(ab)) if aa.get(n) != ab.get(n)]
        if not mud:
            linhas.append((x['v'], '(EZBIND)', 'so_empacotamento'))
        for n in mud:
            tipo = 'novo' if n not in aa else 'sumiu' if n not in ab else 'conteudo'
            linhas.append((x['v'], n, tipo))

    ents_mud = sorted({l[0] for l in linhas})
    print('entradas identicas: %d   com diferenca: %d' % (iguais, len(ents_mud)))
    por_tipo = {}
    for l in linhas:
        por_tipo[l[2]] = por_tipo.get(l[2], 0) + 1
    print('arquivos por tipo de diferenca: %s' % por_tipo)
    ext = {}
    for v, n, t in linhas:
        if t == 'conteudo':
            k = os.path.splitext(n)[1] or n
            ext[k] = ext.get(k, 0) + 1
    print('conteudo mudou, por extensao: %s' % ext)
    if a.csv:
        with open(a.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['entrada_v', 'arquivo', 'diferenca'])
            w.writerows(linhas)
        print('-> %s' % a.csv)
    return 0


if __name__ == '__main__':
    sys.exit(main())

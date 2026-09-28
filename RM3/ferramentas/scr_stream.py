#!/usr/bin/env python3
"""Analisa o stream de comandos de uma cena FaceChat. Somente leitura.

Segmenta em 0xFFFF e resolve qualquer palavra que seja indice de string valido.
"""
import struct


def comandos(p):
    tok = list(struct.unpack_from(f"<{p['n_tok']}H", p['tokens'], 0))
    cmds, cur = [], []
    for t in tok:
        if t == 0xFFFF:
            cmds.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        cmds.append(cur)
    return cmds


def mostra(p, limite=None, so_com_string=False):
    ss = p['strings']
    n = len(ss)
    out = []
    for i, c in enumerate(comandos(p)):
        if not c:
            continue
        refs = []
        for j, w in enumerate(c[1:], 1):
            if 0 <= w < n and ss[w]:
                try:
                    t = ss[w].decode('euc_jp')
                except UnicodeDecodeError:
                    continue
                refs.append((j, w, t))
        if so_com_string and not refs:
            continue
        out.append((i, c, refs))
        if limite and len(out) >= limite:
            break
    return out

#!/usr/bin/env python3
"""Converte para largura dupla os EPISODIOS escolhidos da sinopse (`v2069`) e dos
titulos de capitulo (`v2070`), numa copia da ISO — teste de exibicao do P-85.

A tela de Sinopse mostra o ingles como kanji sem sentido. A hipotese e' que ela
so' desenha caractere de 2 bytes. Esta ferramenta prova ou derruba a hipotese
convertendo so' alguns episodios, o que cabe na folga atual SEM crescer a
entrada (crescer o `v2069` trava o jogo, P-84.2).

Nao muda span, nao muda indice: reconstroi o banco com `oldata.build`, recalcula
o campo C, confere com a guarda do P-83 e escreve no lugar. Recusa o que nao
couber.

Uso:
  sinopse_largura_dupla.py <iso_in> <iso_out> --episodios 0,1 [--aplicar]
"""
import sys, os, gzip, shutil, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import gzip_como_original
from bdi_banco_build_iso import confere_episodios
from largura_dupla import para_largura_dupla
import oldata

SEC = 2048
LBA = 106896
GZ = b'\x1f\x8b\x08'
NUL = b'\x00'


def converte(raw, episodios):
    p = oldata.parse(raw)
    orig = oldata.parse(raw)
    idx = oldata.indices_de_linha(p)          # KeyError se algum C cair no meio: de proposito
    fim = idx[1:] + [len(p['narracao'])]
    n = 0
    for e in episodios:
        p['titulos'][e] = para_largura_dupla(p['titulos'][e])
        for k in range(idx[e], fim[e]):
            novo = para_largura_dupla(p['narracao'][k])
            n += novo != p['narracao'][k]
            p['narracao'][k] = novo
    oldata.recalcular_C(p, idx)
    oldata.recalcular_B(p)
    confere_episodios(orig, p)
    return oldata.build(p), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('--episodios', required=True)
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    eps = [int(x) for x in a.episodios.split(',')]
    saida = os.path.abspath(a.iso_out)
    if saida == os.path.abspath(a.iso_in) or 'Caravan.iso' in os.path.basename(saida):
        print('RECUSADO: a saida nao pode ser a entrada nem a original')
        return 1
    if os.path.exists(saida):
        print('RECUSADO: %s ja existe' % saida)
        return 1

    base = LBA * SEC
    escrever = []
    with open(a.iso_in, 'rb') as f:
        E = {e['v']: e for e in load_index(f, base)[2]}
        for v in (2069, 2070):
            e = E[v]
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            gz = blob[:3] == GZ
            raw = gzip.decompress(blob) if gz else blob
            novo, n = converte(raw, eps)
            saida_b = gzip_como_original(novo, blob) if gz else novo
            print('v%d: %d linhas convertidas, %d -> %d B%s, span %d'
                  % (v, n, len(raw), len(novo), ' (gzip %d B)' % len(saida_b) if gz else '',
                     e['span']))
            if len(saida_b) > e['span']:
                print('RECUSADO: v%d nao cabe no span (faltam %d B)' % (v, len(saida_b) - e['span']))
                return 1
            escrever.append((v, e['off'], saida_b + NUL * (e['span'] - len(saida_b))))
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    shutil.copyfile(a.iso_in, saida)
    with open(saida, 'r+b') as fo:
        for v, off, b in escrever:
            fo.seek(base + off)
            fo.write(b)
    with open(saida, 'rb') as fo:
        for v, off, b in escrever:
            fo.seek(base + off)
            if fo.read(len(b)) != b:
                print('FALHOU a releitura da v%d' % v)
                return 2
    print('escrito e relido: %s' % saida)
    return 0


if __name__ == '__main__':
    sys.exit(main())

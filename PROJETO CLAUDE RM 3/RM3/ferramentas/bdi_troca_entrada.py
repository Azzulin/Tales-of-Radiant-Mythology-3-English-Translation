#!/usr/bin/env python3
"""Copia entradas do `namco.bdi` de uma ISO para outra — ferramenta de BISSECAO.

Para isolar a causa de um travamento entre duas builds (P-78, P-84.2): parte da
ISO nova e devolve so' as entradas suspeitas ao estado da ISO de referencia.
Se o travamento some, a causa esta' nelas.

So' troca entrada cujo span e' IGUAL nas duas ISOs (cada uma lida pelo seu
proprio indice), e escreve o span inteiro no lugar — nada se desloca, o indice
nao muda. Nao e' passo de build: a ISO gerada serve so' para teste.

Uso:
  bdi_troca_entrada.py <iso_base> <iso_fonte> <iso_saida> <v>... [--aplicar]
"""
import sys, os, shutil, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index

SEC = 2048
LBA = 106896


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_base')
    ap.add_argument('iso_fonte')
    ap.add_argument('iso_saida')
    ap.add_argument('v', type=int, nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    saida = os.path.abspath(a.iso_saida)
    if saida in (os.path.abspath(a.iso_base), os.path.abspath(a.iso_fonte)) \
            or 'Caravan.iso' in os.path.basename(saida):
        print('RECUSADO: a saida nao pode ser uma das entradas nem a original')
        return 1
    if os.path.exists(saida):
        print('RECUSADO: %s ja existe' % saida)
        return 1

    base = LBA * SEC
    trocas = []
    with open(a.iso_base, 'rb') as fb, open(a.iso_fonte, 'rb') as ff:
        eb = {e['v']: e for e in load_index(fb, base)[2]}
        ef = {e['v']: e for e in load_index(ff, base)[2]}
        for v in a.v:
            if v not in eb or v not in ef:
                print('RECUSADO: entrada %d nao existe nas duas ISOs' % v)
                return 1
            if eb[v]['span'] != ef[v]['span']:
                print('RECUSADO: entrada %d tem span %d na base e %d na fonte'
                      % (v, eb[v]['span'], ef[v]['span']))
                return 1
            ff.seek(base + ef[v]['off'])
            trocas.append((v, eb[v]['off'], ff.read(ef[v]['span'])))
            print('v%d: %d B da fonte -> offset %d da base' % (v, ef[v]['span'], eb[v]['off']))
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    shutil.copyfile(a.iso_base, saida)
    with open(saida, 'r+b') as fo:
        for v, off, blob in trocas:
            fo.seek(base + off)
            fo.write(blob)
    with open(saida, 'rb') as fo:
        for v, off, blob in trocas:
            fo.seek(base + off)
            if fo.read(len(blob)) != blob:
                print('FALHOU a releitura da entrada %d' % v)
                return 2
    print('escrito e relido: %s' % saida)
    return 0


if __name__ == '__main__':
    sys.exit(main())

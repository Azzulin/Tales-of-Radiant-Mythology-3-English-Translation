#!/usr/bin/env python3
"""Sonda da tela de Sinopse (P-86): troca TRES textos do `v2070` por textos de
teste com EXATAMENTE o mesmo numero de bytes, para que nenhum offset (B, C,
cabecalho) mude, e recomprime pelo mesmo caminho do build.

Numa tela so' responde:
  titulo do ep. 0   `ＴＥＳＴＥ０１`, largura dupla -> a tela desenha letra larga?
  narracao linha 0  largura dupla                 -> idem, no corpo
  narracao linha 1  ASCII puro                    -> a tela desenha 1 byte por letra?
  e, se tudo aparecer, a recompressao do build e' aceita pelo jogo.

Parte de uma ISO cujo `v2070` seja o ORIGINAL (ex.: `RM3-en22-diag-sinopse-jp.iso`).
Escreve no lugar numa copia; recusa se o span nao comportar.

Uso:
  sinopse_sonda.py <iso_in> <iso_out> [--aplicar]
"""
import sys, os, gzip, shutil, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import gzip_como_original
from largura_dupla import para_largura_dupla
import oldata

SEC = 2048
LBA = 106896
NUL = b'\x00'


def do_tamanho(texto_ascii, n, largo):
    """Texto de teste com exatamente n bytes."""
    if largo:
        if n % 2:
            raise ValueError('linha de %d B nao se preenche com caractere de 2 B' % n)
        t = (texto_ascii * 10)[:n // 2]
        return para_largura_dupla(t.encode('ascii'))
    return (texto_ascii * 10)[:n].encode('ascii')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    saida = os.path.abspath(a.iso_out)
    if saida == os.path.abspath(a.iso_in) or 'Caravan.iso' in os.path.basename(saida):
        print('RECUSADO: a saida nao pode ser a entrada nem a original')
        return 1
    if os.path.exists(saida):
        print('RECUSADO: %s ja existe' % saida)
        return 1

    base = LBA * SEC
    with open(a.iso_in, 'rb') as f:
        e = {x['v']: x for x in load_index(f, base)[2]}[2070]
        f.seek(base + e['off'])
        blob = f.read(e['span'])
    raw = gzip.decompress(blob)
    p = oldata.parse(raw)
    if not p['titulos'][0].decode('euc_jp', 'replace').startswith('アドリビトム'):
        print('RECUSADO: o v2070 da entrada nao e o original em japones')
        return 1
    t0, n0, n1 = p['titulos'][0], p['narracao'][0], p['narracao'][1]
    p['titulos'][0] = do_tamanho('TESTE01', len(t0), True)
    p['narracao'][0] = do_tamanho('LINHA 1 LARGURA DUPLA ', len(n0), True)
    p['narracao'][1] = do_tamanho('Linha 2 em ASCII comum. ', len(n1), False)
    novo = oldata.build(p)
    if len(novo) != len(raw) or oldata.parse(novo)['recs'] != oldata.parse(raw)['recs']:
        print('RECUSADO: a sonda mudou tamanho ou offsets')
        return 1
    for rot, x in (('titulo 0', p['titulos'][0]), ('narr 0', p['narracao'][0]), ('narr 1', p['narracao'][1])):
        print('%-9s %2d B  %s' % (rot, len(x), x.decode('euc_jp', 'replace')))
    gz = gzip_como_original(novo, blob)
    if len(gz) > e['span']:
        print('RECUSADO: %d B nao cabe no span %d' % (len(gz), e['span']))
        return 1
    print('gzip %d B de %d; mesmos offsets do original' % (len(gz), e['span']))
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    shutil.copyfile(a.iso_in, saida)
    with open(saida, 'r+b') as fo:
        fo.seek(base + e['off'])
        fo.write(gz + NUL * (e['span'] - len(gz)))
    print('escrito: %s' % saida)
    return 0


if __name__ == '__main__':
    sys.exit(main())

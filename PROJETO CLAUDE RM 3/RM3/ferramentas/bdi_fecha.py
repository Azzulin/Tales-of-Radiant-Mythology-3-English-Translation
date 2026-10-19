#!/usr/bin/env python3
"""Fecha o `namco.bdi` depois do build: cada entrada MODIFICADA ganha o tamanho
exato e o campo A certo (P-87). Ultimo passo sobre o `namco.bdi` na receita.

O campo A do indice (bits 10..0, P-14) e' o padding da entrada:
`tamanho do arquivo = nsect * 2048 - A`. E' esse o tamanho que o jogo le. Medido
na ISO original:
  gzip avulso   1.317 de 1.317   tamanho = fim exato do fluxo gzip
  EZBIND        4.938 de 4.938   tamanho = conteudo arredondado a 64 B (dados
                                  alinhados a 64 ou mais) ou a 4 B (os demais)

Todo build ate' a `en23` preservava o A original. Com o conteudo mudando de
tamanho, o jogo lia o arquivo com o tamanho ANTIGO: no gzip do `v2070` isso
entregava ao descompressor um fim de arquivo errado (a tela de Sinopse virava
lixo ou travava), e em 560 containers EZBIND da `en23` o fim do ultimo arquivo
ficava de fora da leitura.

Aqui, para cada entrada cujo conteudo difere da ISO de referencia (a original),
calcula o tamanho real e reescreve o layout com `nsect = ceil(tamanho/2048)` e
`A = nsect*2048 - tamanho`: o layout nativo do jogo. Entradas nao modificadas
ficam byte a byte. Usa o motor do `bdi_cresce.py` (desloca, reescreve indice,
diretorio e PVD, rele e confere).

Uso:
  bdi_fecha.py <iso_referencia> <iso_in> <iso_out> [--aplicar]
"""
import sys, os, zlib, argparse, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse, alinhamento
import bdi_cresce, oldata, guia2

SEC = 2048
LBA = 106896
GZ = b'\x1f\x8b\x08'
RAW_OLDATA = {2069}             # banco cru cujo tamanho se mede pelo formato
V_GUIA = 2065                   # guia cru: tamanho pelo guia2 (P-89)


def tamanho_gzip(b):
    d = zlib.decompressobj(31)
    d.decompress(b)
    if not d.eof:
        raise ValueError('fluxo gzip nao termina dentro do span')
    return len(b) - len(d.unused_data)


def tamanho_real(v, novo, orig, e_orig):
    if novo[:3] == GZ:
        return tamanho_gzip(novo)
    pe = ezbind_parse(novo)
    if pe:
        regs = pe[2]
        tot = max(r[3] + r[2] for r in regs)
        x = 64 if alinhamento(regs) >= 64 else 4
        return -(-tot // x) * x
    if v in RAW_OLDATA:
        return len(oldata.build(oldata.parse(novo)))
    if v == V_GUIA:             # fim do pool de strings, alinhado a 4 (P-89)
        return guia2.tamanho_projetado(guia2.parse(novo))
    # outro arquivo cru: so' aceita se o conteudo util tem o mesmo tamanho
    if len(novo.rstrip(b'\x00')) <= e_orig['span'] - e_orig['A'] and \
            len(orig.rstrip(b'\x00')) <= e_orig['span'] - e_orig['A']:
        return e_orig['span'] - e_orig['A']
    raise ValueError('entrada crua v%d mudou de tamanho e nao sei medir o formato' % v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_ref')
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    for x in (a.iso_ref, a.iso_in):
        if os.path.abspath(x) == os.path.abspath(a.iso_out):
            print('RECUSADO: a saida nao pode ser uma das entradas')
            return 1
    if 'Caravan.iso' in os.path.basename(a.iso_out):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1

    base = LBA * SEC
    ajuste, mudou, stat = {}, 0, {'encolhe': 0, 'cresce': 0, 'so_A': 0, 'ja_certo': 0}
    with open(a.iso_ref, 'rb') as fr, open(a.iso_in, 'rb') as fi:
        er = {e['v']: e for e in load_index(fr, base)[2]}
        ei = load_index(fi, base)[2]
        for e in ei:
            o = er[e['v']]
            fr.seek(base + o['off'])
            bo = fr.read(o['span'])
            fi.seek(base + e['off'])
            bn = fi.read(e['span'])
            if bo.rstrip(b'\x00') == bn.rstrip(b'\x00'):
                continue
            mudou += 1
            t = tamanho_real(e['v'], bn, bo, o)
            if t > e['span'] or bn[t:].strip(b'\x00'):
                raise ValueError('v%d: tamanho medido %d nao contem o conteudo (span %d)'
                                 % (e['v'], t, e['span']))
            ns = -(-t // SEC)
            an = ns * SEC - t
            if (ns, an) == (e['nsect'], e['A']):
                stat['ja_certo'] += 1
                continue
            stat['encolhe' if ns < e['nsect'] else 'cresce' if ns > e['nsect'] else 'so_A'] += 1
            ajuste[e['v']] = (ns, an)

    with open(a.iso_in, 'rb') as f:
        pl = bdi_cresce.planeja(f, 0, {}, set(), ajuste)
    print('entradas modificadas pelo build: %d' % mudou)
    print('  ja com tamanho e A certos: %d | so o A muda: %d | encolhem: %d | crescem: %d'
          % (stat['ja_certo'], stat['so_A'], stat['encolhe'], stat['cresce']))
    print('namco.bdi: %+d setores; INSDIR desloca %d; ISO %d -> %d setores'
          % (pl['g'], pl['d'], pl['vss'], pl['vss'] + pl['d']))
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    if os.path.exists(a.iso_out):
        print('RECUSADO: %s ja existe' % a.iso_out)
        return 1
    t0 = time.time()
    bdi_cresce.escreve(a.iso_in, a.iso_out, pl)
    falhas = bdi_cresce.confere(a.iso_in, a.iso_out, pl)
    if falhas:
        print('\nFALHOU A CONFERENCIA (%d). A ISO gerada NAO deve ser usada:' % len(falhas))
        for x in falhas[:30]:
            print('   ' + x)
        return 2
    # e a pergunta que importa: o tamanho que o jogo vai ler agora e' o real?
    with open(a.iso_out, 'rb') as f:
        eo = {e['v']: e for e in load_index(f, base)[2]}
        for v, (ns, an) in ajuste.items():
            if (eo[v]['nsect'], eo[v]['A']) != (ns, an):
                print('FALHOU: v%d ficou com nsect/A %d/%d' % (v, eo[v]['nsect'], eo[v]['A']))
                return 2
    print('escrito e conferido em %.0f s: %d entradas com tamanho exato.'
          % (time.time() - t0, len(ajuste)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

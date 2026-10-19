#!/usr/bin/env python3
"""Confere o campo A do indice do bdi contra o TAMANHO REAL do conteudo.

Fecha a pergunta que o P-14 deixou aberta desde o inicio ("o campo A precisa ser
recalculado?"). A resposta, medida:

    tamanho declarado do arquivo = span - A          (A = bytes de enchimento)

Medido na ISO ORIGINAL: das 1.317 entradas que sao um gzip DIRETO (o blob da
entrada comeca em 1f 8b 08), **1.317 terminam o stream exatamente em span - A**.
Zero excecoes. O trailer do gzip (CRC32 + ISIZE) fica colado no fim declarado.

Consequencia pratica: qualquer build que mude o TAMANHO do blob de uma entrada
gzip direta e nao mexa em A deixa o jogo lendo `span - A` bytes de um arquivo
que acabou antes. Os 4 ou 8 ultimos bytes que ele le viram 0x00 — ou seja, o
leitor de gzip encontra CRC=0 e ISIZE=0 no lugar do trailer.

Foi exatamente isso que aconteceu com a entrada v2070 (`oldata.bin`, titulos de
missao) nas ISOs en18/en19. Ver P-82.

O campo A tem 11 bits (0..2047): um arquivo so' pode ser recomprimido se o novo
tamanho cair em (span-2048, span]. Abaixo disso o A nao consegue expressar o
enchimento e a entrada nao pode ser reescrita in-place sem mexer na geometria.

Somente leitura. Nunca abre ISO para escrita.

Uso:
  bdi_campoA_confere.py <iso> [--ez] [--quieto]
"""
import sys, os, struct, zlib, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index

SEC = 2048
LBA = 106896
GZ_MAGIC = b'\x1f\x8b\x08'


def ezbind_total(blob):
    if blob[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < count <= 4000) or len(blob) < 0x10 + count * 16:
        return None
    t = 0
    for i in range(count):
        _, sz, do, _ = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        t = max(t, do + sz)
    return t


def confere(iso, com_ez=False):
    base = LBA * SEC
    gz_ok = gz_curto = gz_longo = gz_erro = 0
    ez_ok = ez_estoura = 0
    falhas = []
    with open(iso, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        for e in entries:
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            decl = e['span'] - e['A']
            if blob[:3] == GZ_MAGIC:
                d = zlib.decompressobj(16 + zlib.MAX_WBITS)
                try:
                    d.decompress(blob)
                except Exception as ex:
                    gz_erro += 1
                    falhas.append((e['v'], 'gzip', 'stream invalido: %s' % ex))
                    continue
                fim = e['span'] - len(d.unused_data)
                if fim == decl:
                    gz_ok += 1
                elif fim < decl:
                    gz_curto += 1
                    falhas.append((e['v'], 'gzip',
                                   'stream acaba em %d, A declara %d — o jogo le '
                                   '%d B de zero no lugar do trailer'
                                   % (fim, decl, decl - fim)))
                else:
                    gz_longo += 1
                    falhas.append((e['v'], 'gzip',
                                   'stream acaba em %d, A declara so %d — LEITURA '
                                   'TRUNCADA em %d B' % (fim, decl, fim - decl)))
            elif com_ez:
                t = ezbind_total(blob)
                if t is None:
                    continue
                if t <= decl:
                    ez_ok += 1
                else:
                    ez_estoura += 1
                    falhas.append((e['v'], 'ezbind',
                                   'dados vao ate %d, A declara %d (+%d)'
                                   % (t, decl, t - decl)))
    return {'gz_ok': gz_ok, 'gz_curto': gz_curto, 'gz_longo': gz_longo,
            'gz_erro': gz_erro, 'ez_ok': ez_ok, 'ez_estoura': ez_estoura,
            'falhas': falhas}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--ez', action='store_true',
                    help='conferir tambem as entradas EZBIND (o casamento nao e '
                         'exato: o A cobre o alinhamento do ultimo arquivo)')
    ap.add_argument('--quieto', action='store_true')
    a = ap.parse_args()

    r = confere(a.iso, a.ez)
    print('%s' % os.path.basename(a.iso))
    print('  gzip direto: %d exatos, %d curtos, %d truncados, %d invalidos'
          % (r['gz_ok'], r['gz_curto'], r['gz_longo'], r['gz_erro']))
    if a.ez:
        print('  ezbind: %d dentro do declarado, %d estourando'
              % (r['ez_ok'], r['ez_estoura']))
    if not a.quieto:
        for v, tipo, msg in r['falhas'][:40]:
            print('    v%-5d %-7s %s' % (v, tipo, msg))
        if len(r['falhas']) > 40:
            print('    ... e mais %d' % (len(r['falhas']) - 40))
    ruim = r['gz_curto'] + r['gz_longo'] + r['gz_erro']
    print('  -> %s' % ('OK' if ruim == 0 else 'REPROVADO (%d entradas gzip)' % ruim))
    return 1 if ruim else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Confere, RELENDO a ISO pronta, que todo `.scr` do `namco.bdi` continua
intacto (P-78).

O lado do EBOOT tem `eboot_verifica_build.py` desde o P-67.12, e foi ele que
pegou uma ISO que passara as cinco guardas e mesmo assim saira corrompida. O
lado do BDI nunca teve o equivalente: `bdi_build_iso.py` confere o round-trip
ANTES de escrever, com o conteudo que ele proprio acabou de montar — o que nao
prova que o que chegou ao disco e' aquilo.

Aqui a ISO e' a fonte. Para cada entrada do indice:

  1. desce por gzip e por EZBIND aninhado ate achar os blocos `FaceChat`;
  2. `fc_parse` — cabecalho coerente, terminador 0xFFFF, tabela de offsets
     dentro do bloco;
  3. `fc_build(p, p['strings']) == bloco` — o round-trip byte a byte;
  4. confere o teto que o formato impoe de verdade: a tabela de offsets e' u16,
     entao o corpo de strings nao pode passar de 65.535 B. `fc_build` so' olha o
     offset da ULTIMA string; uma string longa no fim passa da conta sem ser
     vista.

Uso:
  bdi_verifica_iso.py <iso> [--lba 106896] [--limite N]
"""
import sys, os, zlib, struct, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse, fc_parse, fc_build

SEC = 2048
MAGIC = b'FaceChat'
GZ = b'\x1f\x8b\x08'


def descomprime(b):
    try:
        return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(b)
    except Exception:
        return None


def varre(blob, rot, achados, falhas, prof=0):
    """Desce por gzip/EZBIND e testa todo FaceChat que encontrar."""
    if prof > 6:
        return
    if blob[:3] == GZ:
        d = descomprime(blob)
        if d is None:
            falhas.append((rot, 'gzip nao descomprime'))
            return
        return varre(d, rot + '|gz', achados, falhas, prof + 1)

    if blob[:8] == MAGIC:
        achados[0] += 1
        try:
            p = fc_parse(blob)
        except Exception as ex:
            falhas.append((rot, f'fc_parse: {type(ex).__name__}: {ex}'))
            return
        corpo = sum(len(s) + 1 for s in p['strings'])
        if corpo > 0xFFFF:
            falhas.append((rot, f'corpo de strings {corpo} B > 65535 — '
                                f'a tabela de offsets e u16'))
        try:
            refeito = fc_build(p, p['strings'])
        except Exception as ex:
            falhas.append((rot, f'fc_build: {type(ex).__name__}: {ex}'))
            return
        if refeito != blob[:len(refeito)]:
            falhas.append((rot, f'round-trip NAO bate ({len(p["strings"])} strings)'))
        return

    pe = ezbind_parse(blob)
    if not pe:
        return
    _, _, regs = pe
    for nome, no, sz, do, key in regs:
        sub = blob[do:do + sz]
        if sub[:3] == GZ or sub[:8] == MAGIC or sub[:6] == b'EZBIND':
            varre(sub, f'{rot}/{nome}', achados, falhas, prof + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--lba', type=int, default=106896)
    ap.add_argument('--limite', type=int, default=0,
                    help='parar depois de N entradas (para teste rapido)')
    args = ap.parse_args()

    base = args.lba * SEC
    with open(args.iso, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        print(f'{len(entries)} entradas no indice de {os.path.basename(args.iso)}')
        achados = [0]
        falhas = []
        for i, e in enumerate(entries):
            if args.limite and i >= args.limite:
                break
            f.seek(base + e['off'])
            varre(f.read(e['span']), f"v{e['v']}", achados, falhas)
            if (i + 1) % 1000 == 0:
                print(f'  ... {i+1} entradas, {achados[0]} FaceChat, '
                      f'{len(falhas)} falhas', flush=True)

    print(f'\n{achados[0]} blocos FaceChat conferidos')
    print(f'{len(falhas)} falhas')
    porTipo = collections.Counter(m.split(':')[0].split('(')[0].strip()
                                  for _, m in falhas)
    for t, c in porTipo.most_common():
        print(f'   {c:>5}  {t}')
    for rot, m in falhas[:15]:
        print(f'   [{rot}] {m}')
    return 1 if falhas else 0


if __name__ == '__main__':
    sys.exit(main())

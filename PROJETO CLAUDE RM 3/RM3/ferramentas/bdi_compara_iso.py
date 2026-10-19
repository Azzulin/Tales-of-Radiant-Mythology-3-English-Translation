#!/usr/bin/env python3
"""Compara arquivo a arquivo o `namco.bdi` de duas ISOs (P-78.1).

`bdi_verifica_iso.py` prova que o que está na ISO é internamente coerente. Isto
é outra pergunta, e a que importa quando algo trava: **o que mudou, além do que
devia mudar?**

Desce por gzip e EZBIND aninhado nas duas ISOs em paralelo e, para cada arquivo
interno, diz se ele é igual, se mudou, e — quando muda — se a MOLDURA mudou
junto: nome, offset dentro do EZBIND, tamanho declarado, tamanho do conteúdo
descomprimido. Conteúdo diferente com moldura igual é tradução. Moldura
diferente é remontagem de container, que é onde a corrupção se esconde.

Uso:
  bdi_compara_iso.py <iso_a> <iso_b> [--lba 106896] [--so-suspeitos]
"""
import sys, os, zlib, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse

SEC = 2048
GZ = b'\x1f\x8b\x08'
# extensoes que o projeto traduz de proposito
TRADUZIDAS = ('.scr', '.txz', '.bin')


def gunzip(b):
    try:
        return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(b)
    except Exception:
        return None


def anda(a, b, rot, saida, prof=0):
    """Percorre os dois blobs em paralelo. Só desce onde eles diferem."""
    if a == b or prof > 6:
        return
    if a[:3] == GZ and b[:3] == GZ:
        da, db = gunzip(a), gunzip(b)
        if da is None or db is None:
            saida.append((rot, 'GZIP', 'nao descomprime', len(a), len(b)))
            return
        if len(da) != len(db):
            saida.append((rot, 'gz', f'descomprimido {len(da)}->{len(db)}',
                          len(a), len(b)))
        return anda(da, db, rot, saida, prof + 1)

    pa, pb = ezbind_parse(a), ezbind_parse(b)
    if pa and pb:
        ra, rb = pa[2], pb[2]
        if len(ra) != len(rb):
            saida.append((rot, 'EZBIND', f'{len(ra)} -> {len(rb)} arquivos', 0, 0))
            return
        for (na, noa, sza, doa, ka), (nb, nob, szb, dob, kb) in zip(ra, rb):
            sub = f'{rot}/{na}'
            if na != nb:
                saida.append((sub, 'EZBIND', f'nome {na!r} -> {nb!r}', 0, 0))
                continue
            if (sza, doa) != (szb, dob):
                saida.append((sub, 'MOLDURA',
                              f'off {doa}->{dob}, sz {sza}->{szb}', sza, szb))
            anda(a[doa:doa + sza], b[dob:dob + szb], sub, saida, prof + 1)
        return

    # folha: conteudo puro
    saida.append((rot, 'conteudo', f'{len(a)} -> {len(b)} B',
                  len(a), len(b)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_a')
    ap.add_argument('iso_b')
    ap.add_argument('--lba', type=int, default=106896)
    ap.add_argument('--so-suspeitos', action='store_true',
                    help='esconde o que e claramente traducao (.scr/.txz)')
    args = ap.parse_args()

    base = args.lba * SEC
    fa = open(args.iso_a, 'rb')
    fb = open(args.iso_b, 'rb')
    _, _, ents, _ = load_index(fa, base)
    print(f'{len(ents)} entradas; comparando {os.path.basename(args.iso_a)} '
          f'com {os.path.basename(args.iso_b)}')

    saida = []
    nmud = 0
    for i, e in enumerate(ents):
        fa.seek(base + e['off']); a = fa.read(e['span'])
        fb.seek(base + e['off']); b = fb.read(e['span'])
        if a == b:
            continue
        nmud += 1
        anda(a, b, f"v{e['v']}", saida)
        if nmud % 400 == 0:
            print(f'  ... {nmud} entradas modificadas, {len(saida)} notas',
                  flush=True)
    fa.close(); fb.close()

    print(f'\n{nmud} entradas modificadas, {len(saida)} arquivos internos tocados\n')
    por = collections.Counter(t for _, t, _, _, _ in saida)
    for t, c in por.most_common():
        print(f'  {t:<10} {c}')

    mold = [x for x in saida if x[1] in ('MOLDURA', 'EZBIND', 'GZIP')]
    print(f'\n*** MOLDURA/CONTAINER alterados: {len(mold)} ***')
    for rot, t, m, _, _ in mold[:25]:
        print(f'   [{t}] {rot}: {m}')

    fora = [x for x in saida if x[1] == 'conteudo'
            and not any(x[0].lower().endswith(z) for z in TRADUZIDAS)]
    print(f'\n*** conteudo alterado em arquivo FORA das extensoes traduzidas: '
          f'{len(fora)} ***')
    ext = collections.Counter(os.path.splitext(x[0])[1].lower() for x in fora)
    for z, c in ext.most_common(15):
        print(f'   {z or "(sem extensao)":<16} {c}')
    for rot, t, m, _, _ in fora[:15]:
        print(f'   {rot}: {m}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Devolve ao estado ORIGINAL um conjunto escolhido de entradas do `namco.bdi`,
numa copia da ISO (P-78.1).

Para bissecar. Quando tudo passa nas verificacoes estruturais e mesmo assim o
jogo trava, o jeito de achar a frente culpada e' desligar uma de cada vez —
mudando UMA coisa por ISO, e nada mais.

Copia byte a byte, do `--origem` para a ISO de saida, o `span` inteiro de cada
entrada pedida. Como `span` e' o espaco reservado da entrada (nunca muda), a
geometria da ISO fica intacta: nenhum offset se desloca, nenhum tamanho de
arquivo ISO 9660 precisa ser recalculado.

Aceita numeros `v` soltos, faixas `100-200`, e `--como <outra.iso>`, que reverte
exatamente as entradas em que a saida difere daquela ISO (o jeito curto de dizer
"volte a ser o que a `en12` era aqui").

Uso:
  bdi_reverte_entradas.py <iso_saida> --origem <iso> (--v 17,46,51 | --como <iso>)
                          [--aplicar]
"""
import sys, os, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index

SEC = 2048


def expande(spec):
    out = set()
    for parte in spec.replace(' ', '').split(','):
        if not parte:
            continue
        if '-' in parte:
            a, b = parte.split('-')
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(parte))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_saida')
    ap.add_argument('--origem', required=True)
    ap.add_argument('--v')
    ap.add_argument('--como', help='reverter onde a saida difere DESTA ISO')
    ap.add_argument('--lba', type=int, default=106896)
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    if 'Caravan.iso' in os.path.basename(args.iso_saida):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1
    if os.path.abspath(args.iso_saida) == os.path.abspath(args.origem):
        print('RECUSADO: origem e saida sao a mesma ISO')
        return 1
    if os.path.getsize(args.iso_saida) != os.path.getsize(args.origem):
        print('RECUSADO: as duas ISOs tem tamanhos diferentes')
        return 1

    base = args.lba * SEC
    fo = open(args.origem, 'rb')
    _, _, ents, _ = load_index(fo, base)
    byv = {e['v']: e for e in ents}

    if args.como:
        fc = open(args.como, 'rb')
        fs = open(args.iso_saida, 'rb')
        alvos = []
        for e in ents:
            fc.seek(base + e['off']); a = fc.read(e['span'])
            fs.seek(base + e['off']); b = fs.read(e['span'])
            if a != b:
                alvos.append(e['v'])
        fc.close(); fs.close()
        print(f'{len(alvos)} entradas em que a saida difere de '
              f'{os.path.basename(args.como)}')
    else:
        alvos = sorted(expande(args.v or ''))

    faltam = [v for v in alvos if v not in byv]
    if faltam:
        print(f'RECUSADO: {len(faltam)} entradas nao existem: {faltam[:8]}')
        fo.close(); return 1

    # quais realmente mudam (a saida ja pode estar igual a origem)
    fs = open(args.iso_saida, 'rb')
    reais, bytes_tot = [], 0
    for v in alvos:
        e = byv[v]
        fo.seek(base + e['off']); a = fo.read(e['span'])
        fs.seek(base + e['off']); b = fs.read(e['span'])
        if a != b:
            reais.append(v)
            bytes_tot += sum(1 for x, y in zip(a, b) if x != y)
    fs.close()
    print(f'{len(reais)} de {len(alvos)} entradas voltarao ao original '
          f'({bytes_tot} bytes)')
    for v in reais[:20]:
        print(f'   v{v}  span={byv[v]["span"]}')
    if len(reais) > 20:
        print(f'   ... e mais {len(reais)-20}')

    if not args.aplicar:
        fo.close()
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    with open(args.iso_saida, 'r+b') as g:
        for v in reais:
            e = byv[v]
            fo.seek(base + e['off'])
            g.seek(base + e['off'])
            g.write(fo.read(e['span']))
        g.flush(); os.fsync(g.fileno())

    print('\nconferindo por releitura...')
    ok = 0
    with open(args.iso_saida, 'rb') as g:
        for v in reais:
            e = byv[v]
            fo.seek(base + e['off']); a = fo.read(e['span'])
            g.seek(base + e['off']); b = g.read(e['span'])
            ok += (a == b)
    fo.close()
    print(f'{ok} de {len(reais)} entradas conferem com a origem')
    if ok != len(reais):
        return 1
    print(f'-> {args.iso_saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

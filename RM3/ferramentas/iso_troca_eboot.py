#!/usr/bin/env python3
"""Troca o EBOOT.BIN de uma COPIA da ISO. Exige tamanho identico.

Uso: iso_troca_eboot.py <copia.iso> <lba> <tam_declarado> <eboot_novo> [--aplicar]

DRY-RUN por padrao. Recusa se o tamanho nao casar ao byte — porque nesse caso a
troca mexeria em setores vizinhos e a tabela de arquivos do ISO 9660 teria de ser
recalculada (P-19). Abre a ISO em 'r+b' SOMENTE com --aplicar, e SOMENTE se o
nome do arquivo nao for o da original.
"""
import sys, os, hashlib

SEC = 2048
PROIBIDO = 'Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso'


def main():
    iso, lba, tam, novo = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    aplicar = '--aplicar' in sys.argv
    base = os.path.basename(iso)
    if base == PROIBIDO:
        print(f'RECUSADO: {base} e a ISO ORIGINAL. Trabalhe em copia.')
        return 1

    d = open(novo, 'rb').read()
    print(f'novo EBOOT: {len(d)} bytes  sha256={hashlib.sha256(d).hexdigest()[:16]}')
    if len(d) != tam:
        print(f'RECUSADO: {len(d)} != {tam} declarado na ISO. '
              f'Tamanho diferente exige recalcular ISO 9660.')
        return 1
    off = lba * SEC
    print(f'destino: LBA {lba} = offset {off} .. {off+tam}  ({tam//SEC} setores)')

    with open(iso, 'rb') as f:
        f.seek(off)
        antigo = f.read(tam)
    print(f'antigo:     {len(antigo)} bytes  sha256={hashlib.sha256(antigo).hexdigest()[:16]}'
          f'  magic={antigo[:4]}')
    n_dif = sum(1 for a, b in zip(antigo, d) if a != b)
    print(f'bytes que vao mudar: {n_dif} de {tam} ({100*n_dif/tam:.1f}%)')

    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito.')
        return 0

    with open(iso, 'r+b') as f:
        f.seek(off)
        f.write(d)
        f.flush()
        os.fsync(f.fileno())
    # releitura
    with open(iso, 'rb') as f:
        f.seek(off)
        lido = f.read(tam)
    print(f'\nreleitura: sha256={hashlib.sha256(lido).hexdigest()[:16]}  '
          f'casa? {lido == d}')
    print(f'tamanho da ISO: {os.path.getsize(iso)}')
    return 0 if lido == d else 1


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Troca strings AVULSAS do EBOOT no lugar, dentro da ISO final (P-88).

Para string que nao pertence a bloco nenhum do `eboot_build2.py` (nao esta' numa
tabela de ponteiros catalogada), como `あらすじ%d`, o rotulo da lista da Sinopse.
Reconstruir o EBOOT inteiro por uma string seria desproporcional; esta ferramenta
escreve so' dentro do espaco que a propria string ja ocupa.

Tres guardas por troca, todas medidas no EBOOT da ISO:
  1. os bytes originais no offset tem de ser exatamente os do TSV;
  2. o texto novo + NUL tem de caber no espaco da string: o texto original mais os
     NUL que a seguem ate' o proximo byte nao-zero;
  3. nenhuma referencia (ponteiro u32 ou par lui/addiu) pode apontar para DENTRO
     desse espaco, exceto o inicio: um NUL de alinhamento pode estar servindo de
     "texto vazio" para outro ponteiro (P-76).

Idempotente: se o texto novo ja' esta' la', nao faz nada.

TSV (UTF-8, com cabecalho): foff_eboot  original  traducao  nota
  `original` e `traducao` em texto; o original e' codificado em EUC-JP, e a
  traducao tem de ser ASCII.

Uso:
  eboot_local.py <iso> <lote.tsv> [--aplicar]
"""
import sys, os, csv, struct, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iso_ls, prx

SEC = 2048
NUL = b'\x00'
TAM_ELF = 5862704               # o EBOOT decifrado e' lido ate' aqui (P-19)


def espaco(d, off, n_orig):
    fim = off + n_orig
    while fim < len(d) and d[fim] == 0:
        fim += 1
    return fim - off


def referencias_dentro(d, elf, pares, va, n):
    """Referencias a qualquer byte de va+1 .. va+n-1."""
    alvo = set(range(va + 1, va + n))
    achou = [hex(a) for a in alvo if pares.get(a)]
    for i in range(0, len(d) - 3, 4):
        if struct.unpack_from('<I', d, i)[0] in alvo:
            achou.append('u32@' + hex(i))
    return achou


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('lote')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    if 'Caravan.iso' in os.path.basename(a.iso):
        print('RECUSADO: isto parece a ISO original')
        return 1
    I = iso_ls.Iso(a.iso)
    _, lba, tam, _ = I.find('/PSP_GAME/SYSDIR/EBOOT.BIN')
    I.f.close()
    base = lba * SEC
    with open(a.iso, 'rb') as f:
        f.seek(base)
        d = f.read(tam)
    if d[:4] != b'\x7fELF':
        print('RECUSADO: o EBOOT.BIN da ISO nao e o ELF decifrado')
        return 1
    elf = prx.ler(d[:TAM_ELF])
    pares = prx.pares_hilo(d[:TAM_ELF], elf)

    escrever, ja = [], 0
    with open(a.lote, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            off = int(r['foff_eboot'], 16)
            orig = r['original'].encode('euc_jp')
            novo = r['traducao'].encode('ascii')
            atual = d[off:off + max(len(orig), len(novo))]
            if d[off:off + len(novo) + 1] == novo + NUL and not d[off:off + len(orig)] == orig:
                ja += 1
                continue
            if d[off:off + len(orig)] != orig:
                print('RECUSADO: em 0x%x o EBOOT tem %r, o lote diz %r' % (off, atual, orig))
                return 1
            cabe = espaco(d, off, len(orig))
            if len(novo) + 1 > cabe:
                print('RECUSADO: %r (%d B + NUL) nao cabe nos %d B de 0x%x'
                      % (r['traducao'], len(novo), cabe, off))
                return 1
            va, _ = prx.vaddr_de_fileoff(elf, off)
            dentro = referencias_dentro(d[:TAM_ELF], elf, pares, va, cabe)
            if dentro:
                print('RECUSADO: ha referencia para dentro do espaco de 0x%x: %s' % (off, dentro))
                return 1
            escrever.append((off, novo + NUL * (cabe - len(novo)), r['traducao']))
            print('0x%x: %r -> %r (%d de %d B)' % (off, r['original'], r['traducao'], len(novo) + 1, cabe))
    if not escrever:
        print('nada a fazer (%d ja aplicadas)' % ja)
        return 0
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    with open(a.iso, 'r+b') as f:
        for off, b, _ in escrever:
            f.seek(base + off)
            f.write(b)
    with open(a.iso, 'rb') as f:
        for off, b, _ in escrever:
            f.seek(base + off)
            if f.read(len(b)) != b:
                print('FALHOU a releitura em 0x%x' % off)
                return 2
    print('escrito e relido: %d troca(s).' % len(escrever))
    return 0


if __name__ == '__main__':
    sys.exit(main())

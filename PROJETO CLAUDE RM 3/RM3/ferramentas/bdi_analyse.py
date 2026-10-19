#!/usr/bin/env python3
"""Analise estrutural somente-leitura do inicio do namco.bdi (lido de dentro da ISO).
Uso: bdi_analyse.py <iso> <lba> <size> [bytes_a_analisar]
Nunca escreve.
"""
import sys, struct
from collections import Counter

SEC = 2048

def main():
    iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    span = int(sys.argv[4]) if len(sys.argv) > 4 else 8 << 20
    span = min(span, size)
    with open(iso, 'rb') as f:
        f.seek(lba*SEC)
        data = f.read(span)

    n = len(data) // 2
    u16 = struct.unpack_from(f'<{n}H', data, 0)

    # 1) onde o padrao "u16 pequeno" quebra
    LIM = 0x2000
    first_big = None
    for i, v in enumerate(u16):
        if v >= LIM:
            first_big = i*2
            break
    print(f'span={span}  primeiro u16 >= 0x{LIM:04x} em offset 0x{first_big:x}' if first_big is not None
          else f'span={span}  nenhum u16 >= 0x{LIM:04x}')

    # 2) estatisticas da regiao antes da quebra
    end = first_big if first_big is not None else len(data)
    region = u16[:end//2]
    nz = [v for v in region if v]
    print(f'regiao 0..0x{end:x}: slots={len(region)} nao-zero={len(nz)} '
          f'({100*len(nz)/max(1,len(region)):.1f}%) min={min(nz) if nz else 0} max={max(nz) if nz else 0}')

    # 3) valores repetidos? (hash table de indices unicos vs contagem)
    c = Counter(nz)
    dup = {v: k for v, k in c.items() if k > 1}
    print(f'valores distintos={len(c)}  valores repetidos={len(dup)}  '
          f'exemplos repetidos={list(dup.items())[:5]}')

    # 4) faltantes na sequencia 1..max
    if nz:
        mx = max(nz)
        missing = [v for v in range(1, mx+1) if v not in c]
        print(f'esperado 1..{mx}: presentes={len(c)} faltando={len(missing)} '
              f'primeiros faltando={missing[:10]}')

    # 5) hexdump da fronteira
    if first_big is not None:
        a = max(0, first_big - 64)
        b = min(len(data), first_big + 192)
        print(f'--- fronteira 0x{a:x}..0x{b:x} ---')
        for i in range(a, b, 16):
            row = data[i:i+16]
            h = ' '.join(f'{x:02x}' for x in row)
            t = ''.join(chr(x) if 32 <= x < 127 else '.' for x in row)
            print(f'{i:08x}  {h:<47}  {t}')

if __name__ == '__main__':
    main()

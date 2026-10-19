#!/usr/bin/env python3
"""Janela somente-leitura sobre um arquivo dentro da ISO (sem extrair).
Uso: win.py <iso> <lba> <size> <off> <len> [--hex|--raw]
Nunca escreve.
"""
import sys

SEC = 2048

def read(iso, lba, size, off, ln):
    if off < 0:
        off = size + off
    ln = min(ln, size - off)
    with open(iso, 'rb') as f:
        f.seek(lba*SEC + off)
        return f.read(ln), off

def hexdump(data, base=0):
    out = []
    for i in range(0, len(data), 16):
        row = data[i:i+16]
        h = ' '.join(f'{b:02x}' for b in row)
        a = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        out.append(f'{base+i:010x}  {h:<47}  {a}')
    return '\n'.join(out)

if __name__ == '__main__':
    iso, lba, size, off, ln = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    data, real = read(iso, lba, size, off, ln)
    if '--raw' in sys.argv:
        sys.stdout.buffer.write(data)
    else:
        print(hexdump(data, real))

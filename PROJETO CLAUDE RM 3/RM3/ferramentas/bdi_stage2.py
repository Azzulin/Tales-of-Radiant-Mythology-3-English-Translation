#!/usr/bin/env python3
"""Analise da regiao pos-0x8000 do namco.bdi. Somente leitura."""
import sys, struct
SEC = 2048
iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
span = int(sys.argv[4]) if len(sys.argv) > 4 else (2 << 20)
with open(iso, 'rb') as f:
    f.seek(lba*SEC)
    data = f.read(span)

# --- tabela hash exata 0..0x8000 ---
tab = struct.unpack_from('<16384H', data, 0)
nz = [v for v in tab if v]
print(f'[hash] slots=16384 nao-zero={len(nz)} distintos={len(set(nz))} min={min(nz)} max={max(nz)}')
falta = sorted(set(range(min(nz), max(nz)+1)) - set(nz))
print(f'[hash] faltando no intervalo: {len(falta)} {falta[:10]}')

# --- regiao seguinte como u32 ---
print(f'[dump] 0x7ff0..0x8020 u32:')
for o in range(0x7ff0, 0x8020, 4):
    print(f'   0x{o:05x}  0x{struct.unpack_from("<I", data, o)[0]:08x}')

# --- procurar o alinhamento dos registros: onde ficam os u32 com byte alto 0x80 ---
hits = [o for o in range(0x8000, min(len(data), 0x30000), 4)
        if struct.unpack_from('<I', data, o)[0] >> 24 == 0x80]
if hits:
    d = [hits[i+1]-hits[i] for i in range(min(200, len(hits)-1))]
    from collections import Counter
    print(f'[reg] u32 com byte alto 0x80: {len(hits)} ocorrencias, 1o em 0x{hits[0]:05x}, '
          f'passos mais comuns={Counter(d).most_common(5)}')
    base = hits[0]
    vals = [struct.unpack_from('<I', data, o)[0] & 0x00FFFFFF for o in hits[:400]]
    mono = all(vals[i] <= vals[i+1] for i in range(len(vals)-1))
    print(f'[reg] 24 bits baixos monotonicos nos 400 primeiros? {mono}  '
          f'primeiros={[hex(v) for v in vals[:8]]}  ultimos={[hex(v) for v in vals[-4:]]}')

# --- assumindo registros de 8 B a partir de 0x8014, ver onde a monotonicidade quebra ---
start = hits[0] if hits else 0x8014
n = 0
prev = -1
o = start
while o + 8 <= len(data):
    a = struct.unpack_from('<I', data, o)[0]
    if a >> 24 != 0x80:
        break
    v = a & 0x00FFFFFF
    if v < prev:
        break
    prev = v
    n += 1
    o += 8
print(f'[reg8] registros de 8 B monotonicos a partir de 0x{start:05x}: {n}, '
      f'termina em 0x{o:05x} (proximo u32=0x{struct.unpack_from("<I", data, o)[0]:08x})')
print(f'[reg8] hexdump da borda 0x{o-32:05x}..0x{o+96:05x}')
for i in range(o-32, min(len(data), o+96), 16):
    row = data[i:i+16]
    print(f'{i:08x}  ' + ' '.join(f'{b:02x}' for b in row) + '  ' +
          ''.join(chr(b) if 32 <= b < 127 else '.' for b in row))

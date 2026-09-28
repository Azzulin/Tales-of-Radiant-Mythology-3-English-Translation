#!/usr/bin/env python3
"""Testa a hipotese: header em 0x8000, contagem em 0x8004, registros de 8 B em 0x8014.
Somente leitura."""
import sys, struct
from collections import Counter
SEC = 2048
iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
with open(iso, 'rb') as f:
    f.seek(lba*SEC)
    data = f.read(4 << 20)

count = struct.unpack_from('<I', data, 0x8004)[0]
print(f'contagem em 0x8004 = {count}')
REC = 0x8014
n = count
recs = [struct.unpack_from('<II', data, REC + i*8) for i in range(n)]
flags = Counter(a >> 24 for a, b in recs)
print(f'bytes de flag observados: {flags.most_common(10)}')
lo = [a & 0xFFFFFF for a, b in recs]
mono = all(lo[i] <= lo[i+1] for i in range(n-1))
print(f'low24 monotonico em todos os {n}? {mono}')
print(f'low24 primeiro=0x{lo[0]:06x} ultimo=0x{lo[-1]:06x}')
print(f'segundo u32 (chave?) primeiros={[hex(b) for a,b in recs[:4]]}')
end = REC + n*8
print(f'fim dos registros = 0x{end:05x}')
print('--- 0x%05x..0x%05x ---' % (end-32, end+160))
for i in range(end-32, end+160, 16):
    row = data[i:i+16]
    print(f'{i:08x}  ' + ' '.join(f'{x:02x}' for x in row) + '  ' +
          ''.join(chr(x) if 32 <= x < 127 else '.' for x in row))
# escala: se low24 for setor de 2048, qual o alcance?
print(f'low24 max = {lo[-1]} -> x2048 = {lo[-1]*2048} ; tamanho do bdi = {size}')
print(f'low24 max x 64 = {lo[-1]*64} ; x 256 = {lo[-1]*256} ; x 128 = {lo[-1]*128}')

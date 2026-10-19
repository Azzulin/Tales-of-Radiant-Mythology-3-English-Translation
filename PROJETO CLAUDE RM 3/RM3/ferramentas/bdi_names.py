#!/usr/bin/env python3
"""Procura, entre as entradas do namco.bdi, as que parecem lista de nomes de arquivo.
Somente leitura."""
import sys, struct, re
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from bdi_ls import load_index, SEC

iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
base = lba*SEC
NAME = re.compile(rb'[0-9A-Za-z_\-]{2,32}\.(?:ppt|bin|dat|arc|nbi|gim|tm2|at3|pmf|pgf|txt|prx|tbl|bdi|mdi|ez|gz)', re.I)
with open(iso, 'rb') as f:
    buckets, count, entries, sentinel = load_index(f, base)
    hits = []
    for e in entries:
        if e['size'] < 32 or e['size'] > 4 << 20:
            continue
        f.seek(base + e['off'])
        blob = f.read(min(e['size'], 1 << 20))
        names = NAME.findall(blob)
        if len(names) >= 3:
            hits.append((len(names), e, names[:6], blob[:48]))
    hits.sort(key=lambda t: -t[0])
    print(f'entradas com >=3 nomes de arquivo: {len(hits)}')
    for n, e, sample, head in hits[:25]:
        pr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in head)
        print(f'v={e["v"]:5d} off=0x{e["off"]:08x} size={e["size"]:9d} flag={e["flag"]} '
              f'key={e["key"]:08x} nomes={n:6d}')
        print(f'      head: {pr}')
        print(f'      ex:   {[s.decode("latin1") for s in sample]}')

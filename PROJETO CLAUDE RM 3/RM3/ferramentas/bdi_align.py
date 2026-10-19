#!/usr/bin/env python3
"""Mede o desalinhamento entre o offset do indice e o magic real da entrada.
Somente leitura."""
import sys
from collections import Counter
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from bdi_ls import load_index, SEC

MAGICS = [b'EZBIND', b'NBI\x00', b'FACE', b'\x1f\x8b\x08', b'RIFF', b'PPHD', b'ACE0']
iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
base = lba*SEC
with open(iso, 'rb') as f:
    buckets, count, entries, sentinel = load_index(f, base)
    delta = Counter(); nomag = 0; align = Counter(); gapc = Counter()
    ex = {}
    for i, e in enumerate(entries):
        f.seek(base + e['off'])
        head = f.read(min(128, e['size']))
        found = None
        for m in MAGICS:
            p = head.find(m)
            if p >= 0 and (found is None or p < found[0]):
                found = (p, m)
        if found is None:
            nomag += 1
        else:
            delta[found[0]] += 1
            if found[0] not in ex:
                ex[found[0]] = (e['v'], e['off'], found[1], head[:32])
        align[e['off'] & 0x7ff] = align.get(e['off'] & 0x7ff, 0)
    print(f'entradas={len(entries)}  sem magic conhecido nos 128 B iniciais={nomag}')
    print(f'delta magic-offset: {sorted(delta.items())[:20]}')
    for d in sorted(ex)[:8]:
        v, off, m, h = ex[d]
        pr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in h)
        print(f'  delta={d:3d} ex v={v} off=0x{off:x} magic={m} head="{pr}"')
    # alinhamento dos offsets
    for bits in (2, 4, 6, 8, 11):
        m = (1 << bits) - 1
        print(f'offsets alinhados a {1<<bits} B: '
              f'{sum(1 for e in entries if e["off"] & m == 0)}/{len(entries)}')
    # flag vs magic
    fm = Counter()
    for e in entries[:1500]:
        f.seek(base + e['off']); h = f.read(4)
        fm[(e['flag'], h.hex())] += 1
    print('flag x magic (amostra 1500):', fm.most_common(8))

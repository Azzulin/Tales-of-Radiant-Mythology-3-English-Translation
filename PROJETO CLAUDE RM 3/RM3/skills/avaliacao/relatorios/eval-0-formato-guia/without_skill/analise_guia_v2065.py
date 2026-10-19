#!/usr/bin/env python3
"""Analise da entrada v2065 (GUIA) do namco.bdi -- somente leitura.
Roda no diretorio raiz do projeto (onde esta a ISO e a pasta RM3/).
"""
import sys, struct
from collections import Counter

sys.path.insert(0, 'RM3/ferramentas')
from bdi import load_index, validate

LBA = 106896
SIZE = 992276480
SEC = 2048
NUL = b'\x00'
base = LBA * SEC

with open('Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso', 'rb') as f:
    buckets, count, entries, sentinel = load_index(f, base)
    bad = validate(buckets, count, entries, sentinel, SIZE)
    print('validate() falhas:', bad)

    e = next(x for x in entries if x['v'] == 2065)
    print('entrada v2065:', e)
    off, span, nsect = e['off'], e['span'], e['nsect']
    f.seek(base + off)
    blob = f.read(span)
    print('span reservado (bytes):', span, '/ setores:', nsect, '/ blob lido:', len(blob))

    cnt = struct.unpack_from('<I', blob, 0)[0]
    header_words = struct.unpack_from('<15I', blob, 0)
    print('count (header[0]):', cnt)
    print('header 15xu32 (offsets 0x00..0x38, campo 0x3c fora):')
    for i, w in enumerate(header_words):
        print(f'  +0x{i*4:02x} = {w} (0x{w:x})')

    REC = 36
    TAB = 0x3c
    table_end = TAB + cnt * REC
    print('table_end (0x3c + count*36) =', hex(table_end), table_end)

    def s(a):
        if not (0 <= a < len(blob)):
            return None
        z = blob.find(NUL, a)
        return blob[a:z] if z >= 0 else None

    regs = []
    for i in range(cnt):
        o = TAB + i * REC
        vals = struct.unpack_from('<9I', blob, o)
        regs.append({'i': i, 'id': vals[2], 't_off': vals[0], 'c_off': vals[1], 'resto': vals[3:]})

    print('--- primeiros 5 registros ---')
    for r in regs[:5]:
        print(r)
    print('--- ultimos 5 registros ---')
    for r in regs[-5:]:
        print(r)

    ids = [r['id'] for r in regs]
    print('ids min/max:', min(ids), max(ids))
    print('ids == 0..count-1 ?', ids == list(range(cnt)))
    print('ids sao todos distintos?', len(set(ids)) == len(ids))
    print('primeiros 10 ids:', ids[:10], ' ultimos 10 ids:', ids[-10:])

    resto_cols = list(zip(*[r['resto'] for r in regs]))
    for ci, col in enumerate(resto_cols):
        uniq = sorted(set(col))
        print(f'campo resto[{ci}] (rec+0x{12+ci*4:02x}): min={min(col)} max={max(col)} '
              f'uniq_count={len(uniq)} amostra={uniq[:15]}')

    t_offs = [r['t_off'] for r in regs]
    c_offs = [r['c_off'] for r in regs]
    print('off_titulo min/max:', min(t_offs), max(t_offs),
          'todos dentro do blob?', all(0 <= o < len(blob) for o in t_offs))
    print('off_corpo min/max:', min(c_offs), max(c_offs),
          'todos dentro do blob?', all(0 <= o < len(blob) for o in c_offs))
    print('off_titulo estritamente crescente?', all(t_offs[i] < t_offs[i+1] for i in range(len(t_offs)-1)))
    print('off_corpo estritamente crescente?', all(c_offs[i] < c_offs[i+1] for i in range(len(c_offs)-1)))
    print('menor offset de string vs table_end:', min(t_offs + c_offs), 'table_end=', table_end)

    cnt_t = Counter(t_offs)
    cnt_c = Counter(c_offs)
    print('off_titulo duplicados:', {k: v for k, v in cnt_t.items() if v > 1})
    print('off_corpo duplicados:', {k: v for k, v in cnt_c.items() if v > 1})
    print('offsets compartilhados entre titulo e corpo:', set(t_offs) & set(c_offs))

    def dec(b):
        if b is None:
            return None
        try:
            return b.decode('euc_jp')
        except Exception as ex:
            return f'ERRO {ex}: {b[:40]!r}'

    for i in [0, 1, 2, cnt - 1]:
        r = regs[i]
        traw, craw = s(r['t_off']), s(r['c_off'])
        print(f"reg[{i}] id={r['id']} t_off={r['t_off']} len={len(traw) if traw else None} titulo={dec(traw)!r}")
        print(f"reg[{i}] id={r['id']} c_off={r['c_off']} len={len(craw) if craw else None} corpo={dec(craw)!r}")

    ends = []
    for r in regs:
        for o in (r['t_off'], r['c_off']):
            z = blob.find(NUL, o)
            if z >= 0:
                ends.append(z + 1)
    used_end = max(ends) if ends else table_end
    print('fim do ultimo NUL de string (used_end):', used_end, '/ span reservado:', span, '/ folga:', span - used_end)
    tail = blob[used_end:used_end + 64]
    print('64B apos ultima string:', tail)
    print('tudo depois de used_end e zero?', all(b == 0 for b in blob[used_end:]))

    all_offs = sorted(set(t_offs) | set(c_offs))
    gaps = []
    for i in range(len(all_offs) - 1):
        z = blob.find(NUL, all_offs[i])
        strend = z + 1 if z >= 0 else all_offs[i]
        gaps.append(all_offs[i + 1] - strend)
    print('gaps entre strings consecutivas (amostra 30):', gaps[:30])
    print('valores unicos de gap (ate 15):', sorted(set(gaps))[:15])
    print('todos os offsets de string multiplos de 4?', all(o % 4 == 0 for o in all_offs))
    print('primeiro offset de string == table_end?', all_offs[0] == table_end, all_offs[0])

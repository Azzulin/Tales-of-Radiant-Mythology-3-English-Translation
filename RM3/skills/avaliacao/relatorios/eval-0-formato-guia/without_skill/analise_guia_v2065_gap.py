#!/usr/bin/env python3
import sys, struct
sys.path.insert(0, 'RM3/ferramentas')
from bdi import load_index

LBA = 106896
SIZE = 992276480
SEC = 2048
NUL = b'\x00'
base = LBA * SEC

with open('Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso', 'rb') as f:
    buckets, count, entries, sentinel = load_index(f, base)
    e = next(x for x in entries if x['v'] == 2065)
    f.seek(base + e['off'])
    blob = f.read(e['span'])

cnt = struct.unpack_from('<I', blob, 0)[0]
REC, TAB = 36, 0x3c
table_end = TAB + cnt * REC

regs = []
for i in range(cnt):
    o = TAB + i * REC
    vals = struct.unpack_from('<9I', blob, o)
    regs.append({'i': i, 't_off': vals[0], 'c_off': vals[1], 'id': vals[2], 'resto': vals[3:]})

t_offs = [r['t_off'] for r in regs]
first_str = min(t_offs)
gap_start, gap_end = table_end, first_str
gap = blob[gap_start:gap_end]
print(f'GAP entre table_end=0x{gap_start:x}({gap_start}) e primeiro_titulo=0x{gap_end:x}({gap_end}); tamanho={len(gap)}')
print('gap todo zero?', all(b == 0 for b in gap))
print('gap primeiros 64 bytes hex:', gap[:64].hex())
print('gap ultimos 64 bytes hex:', gap[-64:].hex())
# ver se gap tem padrao de u32 repetido / crescente
if len(gap) % 4 == 0:
    words = struct.unpack_from(f'<{len(gap)//4}I', gap, 0)
    nz = [w for w in words if w != 0]
    print('gap como u32: total', len(words), 'nao-zero:', len(nz), 'amostra nao-zero (ate 20):', nz[:20])
if len(gap) % 2 == 0:
    hw = struct.unpack_from(f'<{len(gap)//2}H', gap, 0)
    nz = [w for w in hw if w != 0]
    print('gap como u16: total', len(hw), 'nao-zero:', len(nz), 'amostra nao-zero (ate 30):', nz[:30])

# hex/bitfield de id e resto para eyeball
print('--- id e resto em hex (primeiros 15) ---')
for r in regs[:15]:
    print(r['i'], 'id=0x%08x' % r['id'], 'hi16=%d lo16=%d' % (r['id']>>16, r['id']&0xffff),
          'resto_hex=', [f'0x{x:08x}' for x in r['resto']])
print('--- id e resto em hex (ultimos 5) ---')
for r in regs[-5:]:
    print(r['i'], 'id=0x%08x' % r['id'], 'hi16=%d lo16=%d' % (r['id']>>16, r['id']&0xffff),
          'resto_hex=', [f'0x{x:08x}' for x in r['resto']])

# monotonicidade de resto[1] (indice 1 == rec+0x10)
col1 = [r['resto'][1] for r in regs]
print('resto[1] (rec+0x10) e nao-decrescente?', all(col1[i] <= col1[i+1] for i in range(len(col1)-1)))
print('resto[1] valores (primeiros 30):', col1[:30])

# resto[0] hi16/lo16
col0 = [r['resto'][0] for r in regs]
print('resto[0] hi16/lo16 (primeiros 15):', [(v>>16, v&0xffff) for v in col0[:15]])
print('resto[0] hi16/lo16 (ultimos 5):', [(v>>16, v&0xffff) for v in col0[-5:]])

# resto[5] hi16/lo16
col5 = [r['resto'][5] for r in regs]
print('resto[5] hi16/lo16 (primeiros 15):', [(v>>16, v&0xffff) for v in col5[:15]])
uniq5 = sorted(set(col5))
print('resto[5] uniq (ate 30):', uniq5[:30])

# id hi16 groups: contagem de registros por hi16(id)
from collections import Counter
hi_counts = Counter(r['id'] >> 16 for r in regs)
print('grupos por id_hi16 (categoria):', sorted(hi_counts.items()))

# checar se id_lo16 eh sequencial global 1..count usando i
lo_all = sorted(r['id'] & 0xffff for r in regs)
print('id_lo16 ordenado eh 1..? :', lo_all[:5], '...', lo_all[-5:], 'len=', len(lo_all), 'set igual a range(1,212)?', set(lo_all) == set(range(1,212)))

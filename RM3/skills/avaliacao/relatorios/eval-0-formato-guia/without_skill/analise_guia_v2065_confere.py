#!/usr/bin/env python3
import sys, struct
sys.path.insert(0, 'RM3/ferramentas')
from bdi import load_index

LBA = 106896
SIZE = 992276480
SEC = 2048
base = LBA * SEC

with open('Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso', 'rb') as f:
    buckets, count, entries, sentinel = load_index(f, base)
    idx = next(i for i, x in enumerate(entries) if x['v'] == 2065)
    e = entries[idx]
    prev_e = entries[idx-1]
    next_e = entries[idx+1]
    print('anterior (v=%d): sect=%d off=%d nsect=%d' % (prev_e['v'], prev_e['sect'], prev_e['off'], prev_e['nsect']))
    print('v2065        : sect=%d off=%d nsect=%d span=%d' % (e['sect'], e['off'], e['nsect'], e['span']))
    print('proxima (v=%d): sect=%d off=%d' % (next_e['v'], next_e['sect'], next_e['off']))
    print('confirma: proxima.sect - v2065.sect == nsect?', next_e['sect'] - e['sect'] == e['nsect'])
    print('confirma: espaco de v2065 e "buraco" ate a proxima entrada, sem folga extra reservada')

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

NUL = b'\x00'
def s(a):
    z = blob.find(NUL, a)
    return blob[a:z] if z >= 0 else None

t_offs = sorted(r['t_off'] for r in regs)
c_offs = sorted(r['c_off'] for r in regs)
pool_titulos_ini, pool_titulos_fim = t_offs[0], None
z = blob.find(NUL, t_offs[-1]); pool_titulos_fim = z+1
pool_corpos_ini = c_offs[0]
z = blob.find(NUL, c_offs[-1]); pool_corpos_fim = z+1
print('pool titulos: [%d, %d) tamanho=%d' % (pool_titulos_ini, pool_titulos_fim, pool_titulos_fim-pool_titulos_ini))
print('pool corpos : [%d, %d) tamanho=%d' % (pool_corpos_ini, pool_corpos_fim, pool_corpos_fim-pool_corpos_ini))
print('titulos terminam exatamente onde corpos comecam (ou perto, alinhado a 4)?', pool_corpos_ini - pool_titulos_fim, 'bytes de folga')

# corpo vazio -> quantos registros tem corpo de tamanho 0?
vazios = [r['i'] for r in regs if s(r['c_off']) == b'']
print('registros com corpo vazio (string de tamanho 0):', len(vazios), 'indices (ate 15):', vazios[:15])
titvazios = [r['i'] for r in regs if s(r['t_off']) == b'']
print('registros com titulo vazio:', len(titvazios))

# soma de bytes de texto (sem NUL) só para dimensionar o "orcamento"
tot_tit = sum(len(s(r['t_off']) or b'') for r in regs)
tot_corpo = sum(len(s(r['c_off']) or b'') for r in regs)
print('bytes de texto (sem NUL/padding): titulos=%d corpos=%d total=%d' % (tot_tit, tot_corpo, tot_tit+tot_corpo))
print('span reservado=%d; usado ate agora=%d; folga bruta=%d' % (e['span'], pool_corpos_fim, e['span']-pool_corpos_fim))

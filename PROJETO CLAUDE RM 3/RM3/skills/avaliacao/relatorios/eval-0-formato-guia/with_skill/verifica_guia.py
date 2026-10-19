#!/usr/bin/env python3
"""Verificacao do formato GUIA (P-28 -> v2). Somente leitura da ISO.

Uso: verifica_guia.py <iso> <lba> <size>
"""
import sys, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guia2

NUL = b'\x00'


def carrega(iso, lba, size, v=2065):
    sys.path.insert(0, 'RM3/ferramentas')
    import bdi
    with open(iso, 'rb') as f:            # SOMENTE LEITURA
        base = lba * 2048
        buckets, count, entries, sent = bdi.load_index(f, base)
        bad = bdi.validate(buckets, count, entries, sent, size)
        if bad:
            raise SystemExit('indice do bdi reprovou: %s' % bad)
        e = [x for x in entries if x['v'] == v][0]
        f.seek(base + e['off'])
        return f.read(e['span']), e


def main():
    iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    data, e = carrega(iso, lba, size)
    print('entrada v2065: off=%d span=%d nsect=%d' % (e['off'], e['span'], e['nsect']))

    p = guia2.parse(data, strict=True)
    print('parse OK (modo strict): count=%d, avisos=%s' % (p['count'], p['avisos']))
    print('mapa de regioes:')
    print('  0x00000..0x%05x  cabecalho (%d B)  resto=%s' % (guia2.HDR, guia2.HDR, p['hdr_resto']))
    print('  0x%05x..0x%05x  tabela %d x %d B' % (guia2.HDR, p['ord_off'], p['count'], guia2.REC))
    print('  0x%05x..0x%05x  pool de ordem %d x u32' % (p['ord_off'], p['pool_off'], len(p['ordem'])))
    print('  0x%05x..0x%05x  pool de strings (%d titulos + %d corpos)'
          % (p['pool_off'], p['fim_pool'], p['count'], p['count']))
    print('  0x%05x..0x%05x  cauda: %d B, tudo zero? %s'
          % (p['fim_pool'], len(data), len(p['cauda']), set(p['cauda']) <= {0}))

    # ---- ROUND-TRIP
    r = guia2.build(p)
    print('ROUND-TRIP byte-perfeito: %s (%d vs %d bytes)' % (r == data, len(r), len(data)))
    if r != data:
        d = [i for i in range(min(len(r), len(data))) if r[i] != data[i]]
        print('  primeiras divergencias:', [hex(i) for i in d[:10]])

    # ---- invariante aritmetico explicito
    print('invariante: 0x20 + %d*36 = 0x%x == inicio do pool de ordem 0x%x -> %s'
          % (p['count'], guia2.HDR + p['count'] * guia2.REC, p['ord_off'],
             guia2.HDR + p['count'] * guia2.REC == p['ord_off']))
    print('invariante: pool de ordem = permutacao de 1..%d -> %s'
          % (p['count'] - 1, sorted(p['ordem']) == list(range(1, p['count']))))
    print('invariante: soma dos filho_num = %d == count-1 = %d -> %s'
          % (sum(r_['filho_num'] for r_ in p['regs']), p['count'] - 1,
             sum(r_['filho_num'] for r_ in p['regs']) == p['count'] - 1))

    # ---- arvore
    raiz = [r_ for r_ in p['regs'] if r_['parent'] == guia2.NOPARENT]
    print('nos com parent=0xffff (raiz): %s' % [r_['id'] for r_ in raiz])
    print('id == indice do registro em todos? %s'
          % all(r_['id'] == r_['i'] for r_ in p['regs']))
    prof = {}
    for r_ in p['regs']:
        d, cur = 0, r_
        while cur['parent'] != guia2.NOPARENT and d < 20:
            cur = p['regs'][cur['parent']]; d += 1
        prof[r_['id']] = d
    print('profundidades:', sorted(set(prof.values())),
          'folhas:', sum(1 for r_ in p['regs'] if r_['filho_num'] == 0))

    # ---- os campos nao identificados: sao cache de conteudo?
    print('--- campos nao identificados: podem ser cache do texto? ---')
    for nome in ('A', 'B', 'C', 'D'):
        col = [r_[nome] for r_ in p['regs']]
        print(' %s: distintos=%d  min=%d max=%d  zeros=%d/%d'
              % (nome, len(set(col)), min(col), max(col), col.count(0), len(col)))
        for alvo, rot in ((lambda r_: len(r_['titulo']), 'len(titulo)'),
                          (lambda r_: len(r_['corpo']), 'len(corpo)'),
                          (lambda r_: len(r_['titulo']) + 1, 'len(titulo)+1'),
                          (lambda r_: len(r_['corpo']) + 1, 'len(corpo)+1'),
                          (lambda r_: r_['corpo'].count(b'\n'), 'linhas(corpo)'),
                          (lambda r_: r_['corpo'].count(b'\n') + 1, 'linhas(corpo)+1')):
            ig = sum(1 for r_ in p['regs'] if r_[nome] == alvo(r_))
            if ig > len(col) // 20:
                print('      %s == %s em %d/%d registros' % (nome, rot, ig, len(col)))
        u16 = [(c & 0xffff, c >> 16) for c in col]
        print('      como u16: lo distintos=%d hi distintos=%d hi!=0 em %d'
              % (len(set(a for a, b in u16)), len(set(b for a, b in u16)),
                 sum(1 for a, b in u16 if b)))
        print('      valores (reg 0..11):', col[:12])

    # ---- orcamento de espaco
    proj = guia2.tamanho_projetado(p)
    print('--- orcamento ---')
    print('conteudo atual: %d B; span reservado pelo indice: %d B; folga = %d B'
          % (proj, e['span'], e['span'] - proj))
    tb = sum(guia2._align4(len(r_['titulo']) + 1) for r_ in p['regs'])
    cb = sum(guia2._align4(len(r_['corpo']) + 1) for r_ in p['regs'])
    print('bytes de titulo=%d, de corpo=%d, total texto=%d' % (tb, cb, tb + cb))

    # ---- amostra
    print('--- amostra (id, parent, filhos, titulo) ---')
    for r_ in p['regs'][:6] + p['regs'][-2:]:
        print('  %3d p=%5d f=[%d..%d) %r' % (r_['id'], r_['parent'], r_['filho_ini'],
              r_['filho_ini'] + r_['filho_num'], guia2.decode(r_['titulo'])))

    # ---- teste negativo: o parser rejeita conteudo que nao fecha?
    print('--- teste negativo ---')
    ruim = bytearray(data); ruim[guia2.HDR + 28] ^= 0x04   # mexe num off_titulo
    try:
        guia2.parse(bytes(ruim), strict=True); print('  FALHOU: aceitou offset corrompido')
    except ValueError as ex:
        print('  rejeitou offset corrompido:', str(ex)[:70])
    ruim2 = bytearray(data); ruim2[p['ord_off']] ^= 0xff
    try:
        guia2.parse(bytes(ruim2), strict=True); print('  FALHOU: aceitou pool de ordem corrompido')
    except ValueError as ex:
        print('  rejeitou pool de ordem corrompido:', str(ex)[:70])


main()

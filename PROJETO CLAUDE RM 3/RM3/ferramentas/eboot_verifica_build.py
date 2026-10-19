#!/usr/bin/env python3
"""Confere um `EBOOT_dec_enNN.bin` recem-construido, relendo-o (P-67.12).

As cinco guardas do `eboot_build2.py` ja passaram quando isto roda — e mesmo
assim uma ISO saiu corrompida em 22/09, porque nenhuma delas le o resultado.
Esta ferramenta le:

  1. ponteiro a ponteiro: cada um aponta para a traducao que o lote mandou?
     (`(verbatim)` tem de ler os bytes japoneses ORIGINAIS daquela string)
  2. a tabela de codigo de personagem continua intacta?
  3. mudou algum byte FORA das arenas declaradas e fora dos proprios ponteiros?
     — e' esta que prova que campo de registro e dado vizinho sobreviveram
  4. o tamanho do arquivo nao mudou (ou, com transbordo, o ELF tem o 2o PT_LOAD
     certo, `elf_segmento.confere`, e o resto do arquivo e' o LIMPO; P-91)

Uso:
  eboot_verifica_build.py <eboot_novo> <eboot_limpo> <lote.csv>...
"""
import sys, os, csv, struct, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elf_segmento

DELTA = 0x08803000
ELF_FIM = 5862704
NUL = b'\x00'
BS = chr(92)
BARRA_N = BS + 'n'
BARRA_T = BS + 't'
BARRA_RN = BS + 'r' + BS + 'n'
TAB_CODIGO = (0x08C92FF8, 0x08C934C8)


def unesc(t):
    return (t.replace(BARRA_RN, chr(13) + chr(10))
             .replace(BARRA_N, chr(10))
             .replace(BARRA_T, chr(9)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('novo')
    ap.add_argument('limpo')
    ap.add_argument('lotes', nargs='+')
    args = ap.parse_args()

    novo = open(args.novo, 'rb').read()
    limpo = open(args.limpo, 'rb').read()

    rows = []
    for L in args.lotes:
        with open(L, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if not r.get('bloco'):
                    r['bloco'] = 'criacao'
                rows.append(r)

    ok = ruim = verb = 0
    ex = []
    for r in rows:
        vp = int(r['va_ponteiro'], 16)
        w, = struct.unpack_from('<I', novo, vp - DELTA)
        try:
            p = elf_segmento.fileoff(novo, w)
        except ValueError:
            ruim += 1
            if len(ex) < 6:
                ex.append((r['bloco'], vp, 'aponta para fora: 0x%08X' % w))
            continue
        if r['traducao'] == '(verbatim)':
            n = int(r['bytes_jp'])
            orig = limpo[int(r['va_string'], 16) - DELTA:][:n]
            if novo[p:p + n] == orig:
                ok += 1
                verb += 1
            else:
                ruim += 1
                if len(ex) < 6:
                    ex.append((r['bloco'], vp, 'verbatim nao bate'))
        else:
            lido = novo[p:novo.find(NUL, p)].decode('euc_jp', 'replace')
            if lido == unesc(r['traducao']):
                ok += 1
            else:
                ruim += 1
                if len(ex) < 6:
                    ex.append((r['bloco'], vp, 'lido=' + repr(lido[:36])))
    print('1) releitura: %d ponteiros corretos (%d verbatim), %d divergentes'
          % (ok, verb, ruim))
    for b, vp, m in ex:
        print('     [%s] 0x%08X %s' % (b, vp, m))

    a, b = TAB_CODIGO[0] - DELTA, TAB_CODIGO[1] - DELTA
    intacta = limpo[a:b] == novo[a:b]
    print('2) tabela de codigo de personagem intacta: %s' % intacta)

    porb = {}
    for r in rows:
        porb.setdefault(r['bloco'], []).append(r)
    faixas = []
    for _, rs in porb.items():
        if rs[0].get('arena_ini') and rs[0].get('arena_fim'):
            faixas.append((int(rs[0]['arena_ini'], 16), int(rs[0]['arena_fim'], 16)))
        else:
            vs = [(int(x['va_string'], 16), int(x['bytes_jp'])) for x in rs]
            faixas.append((min(v for v, _ in vs), max(v + n + 1 for v, n in vs)))
    em = bytearray(ELF_FIM)
    for ai, af in faixas:
        for q in range(max(0, ai - DELTA), min(ELF_FIM, af - DELTA)):
            em[q] = 1
    seg = elf_segmento.segmento(novo)
    sp = elf_segmento.bytes_do_cabecalho(novo) if seg else set()
    for r in rows:
        vp = int(r['va_ponteiro'], 16) - DELTA
        for k in range(4):
            sp.add(vp + k)
    dif = [q for q in range(ELF_FIM)
           if limpo[q] != novo[q] and not em[q] and q not in sp]
    print('3) bytes mudados fora de arena e fora de ponteiro: %d' % len(dif))
    if dif:
        print('     primeiros: %s' % [hex(q + DELTA) for q in dif[:6]])
    if seg:
        va, off, n = seg
        estrut = elf_segmento.confere(novo, limpo)
        cauda_ok = novo[ELF_FIM:len(limpo)] == limpo[ELF_FIM:]
        n_t = sum(1 for r in rows if r['traducao'] != '(verbatim)' and
                  va <= struct.unpack_from('<I', novo, int(r['va_ponteiro'], 16) - DELTA)[0] < va + n)
        print('4) tamanho %d = LIMPO %d + segmento de %d B em 0x%08X (%d ponteiros la); '
              'estrutura: %s; cauda do dump intacta: %s'
              % (len(novo), len(limpo), n, va, n_t, 'ok' if not estrut else '; '.join(estrut), cauda_ok))
        tam_ok = not estrut and cauda_ok
    else:
        print('4) tamanho %d (LIMPO %d)' % (len(novo), len(limpo)))
        tam_ok = len(novo) == len(limpo)

    ing = {r['traducao'] for r in rows if r['traducao'] != '(verbatim)'}
    jp = {r['va_string'] for r in rows if r['traducao'] == '(verbatim)'}
    print('\nstrings distintas em ingles: %d' % len(ing))
    print('strings deixadas em japones: %d' % len(jp))
    falhou = ruim or not intacta or dif or not tam_ok
    print('\n%s' % ('FALHOU' if falhou else 'TUDO CONFERE'))
    return 1 if falhou else 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Auditoria do EBOOT: TODA string japonesa de `.rodata`/`.data` e como o jogo a
alcanca (P-92).

O inventario do EBOOT (P-54, P-68, `eboot_cobertura.py`) partiu de tabelas de
ponteiro: um u32 no binario que vale o endereco da string. Mas o codigo tambem
monta endereco com um par `lui rX,hi` + `addiu/ori/lw.. rY,rX,lo` — e uma
string alcancada SO' assim nunca aparece numa tabela. `あらすじ%d` (P-88) era
uma; `%sをパーティに参加させますか？` e a mensagem de liberacao do Colosseum
sao outras (vistas em jogo na `en29`).

Para cada string EUC-JP com japones (NUL-terminada, comecando depois de um NUL),
conta:
  ptr     u32 alinhados no arquivo que valem o endereco do inicio
  codigo  pares lui/lo, por fluxo linear (registrador morto ao ser reescrito,
          limpo depois do delay slot de j/jal/jr — o `addiu a0` do delay slot
          do `jal printf` e' o caso mais comum)
e se o endereco ja e' alvo de algum lote do build (`--lotes`) ou do
`dados/eboot_local.tsv`.

Le o EBOOT dado como fonte do texto (de preferencia o LIMPO: os enderecos dos
lotes sao do LIMPO). So' le; escreve o CSV pedido.

Uso:
  eboot_auditoria_codigo.py <eboot_limpo> --lotes <csv...> [--local dados/eboot_local.tsv]
                            [--csv saida.csv]
"""
import sys, os, csv, re, struct, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prx

DELTA = 0x08803000
ELF_FIM = 5862704
JP = re.compile('[぀-ヿ一-鿿！-～]')
LO = {0x09, 0x0d, 0x23, 0x2b, 0x20, 0x24, 0x21, 0x25, 0x28, 0x29, 0x31, 0x39}
NAO_ESCREVE_RT = {0x2b, 0x28, 0x29, 0x39, 0x04, 0x05, 0x01, 0x06, 0x07,
                  0x14, 0x15, 0x16, 0x17, 0x02, 0x03}


def pares_codigo(d, ini, fim):
    """{endereco: n} de pares lui/lo por fluxo linear em d[ini:fim]."""
    res = collections.Counter()
    pend = {}
    limpar = 0
    for p in range(ini, fim, 4):
        w = struct.unpack_from('<I', d, p)[0]
        op, rs, rt, rd = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        if op == 0x0f:
            pend[rt] = w & 0xFFFF
        else:
            if op in LO and rs in pend:
                lo = w & 0xFFFF
                if op != 0x0d and lo & 0x8000:
                    lo -= 0x10000
                res[((pend[rs] << 16) + lo) & 0xFFFFFFFF] += 1
            if op == 0:
                if (w & 63) not in (8, 9):
                    pend.pop(rd, None)
            elif op not in NAO_ESCREVE_RT:
                pend.pop(rt, None)
        if limpar:
            limpar -= 1
            if not limpar:
                pend.clear()
        if op in (2, 3) or (op == 0 and (w & 63) in (8, 9)):
            limpar = 1                      # o delay slot ainda executa
    return res


def strings_jp(d, ini, fim):
    out = []
    q = ini
    while q < fim:
        if d[q] == 0:
            q += 1
            continue
        z = d.find(b'\x00', q, fim)
        if z < 0:
            break
        if q == ini or d[q - 1] == 0:
            b = d[q:z]
            try:
                t = b.decode('euc_jp')
            except UnicodeDecodeError:
                t = None
            if t and JP.search(t) and all(c >= ' ' or c in '\n\t' for c in t):
                out.append((q, t, len(b)))
        q = z + 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--lotes', nargs='*', default=[])
    ap.add_argument('--local', default=None)
    ap.add_argument('--csv', default=None)
    a = ap.parse_args()
    d = open(a.eboot, 'rb').read()[:ELF_FIM]
    elf = prx.ler(d)
    sec = {s['name']: s for s in elf['secs']}
    txt = sec['.text']
    cod = pares_codigo(d, txt['off'], txt['off'] + txt['size'])
    for nm in ('.init', '.fini'):
        if nm in sec:
            cod.update(pares_codigo(d, sec[nm]['off'], sec[nm]['off'] + sec[nm]['size']))
    ptr = collections.Counter()
    for q in range(0x1000, ELF_FIM - 3, 4):
        ptr[struct.unpack_from('<I', d, q)[0]] += 1

    em_lote = set()
    for L in a.lotes:
        for r in csv.DictReader(open(L, encoding='utf-8')):
            em_lote.add(int(r['va_string'], 16))
    local = set()
    if a.local:
        for r in csv.DictReader(open(a.local, encoding='utf-8'), delimiter='\t'):
            local.add(int(r['foff_eboot'], 16) + DELTA)

    linhas = []
    for nm in ('.rodata', '.data'):
        s = sec[nm]
        for q, t, n in strings_jp(d, s['off'], s['off'] + s['size']):
            va = q + DELTA
            c, pt = cod.get(va, 0), ptr.get(va, 0)
            if va in em_lote:
                cl = 'lote'
            elif va in local:
                cl = 'eboot_local'
            elif c and not pt:
                cl = 'SO_CODIGO'
            elif pt:
                cl = 'ptr_fora_de_lote'
            else:
                cl = 'sem_referencia'
            linhas.append({'va': '0x%08X' % va, 'foff': '0x%X' % q, 'secao': nm, 'bytes': n,
                           'refs_codigo': c, 'refs_ptr': pt, 'classe': cl, 'texto': t.replace('\n', '\\n')})
    cont = collections.Counter(l['classe'] for l in linhas)
    print('%d strings japonesas em .rodata/.data' % len(linhas))
    for k, v in cont.most_common():
        print('  %-18s %d' % (k, v))
    if a.csv:
        with open(a.csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        print('-> %s' % a.csv)
    return 0


if __name__ == '__main__':
    sys.exit(main())

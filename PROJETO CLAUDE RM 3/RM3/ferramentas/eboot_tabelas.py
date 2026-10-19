#!/usr/bin/env python3
"""Encontra TODAS as tabelas de ponteiro para string em .data / .rodata (P-42).

Uma tabela e' uma corrida de >= MIN u32 consecutivas cujo valor aponta para o
inicio de uma string plausivel dentro do modulo. Somente leitura.

Uso: eboot_tabelas.py <eboot_dec> [min_corrida] [saida.csv]
"""
import sys, csv, struct, collections

ELF_FIM = 5862704
DELTA = 0x08803000
VA_LO, VA_HI = 0x08804000, 0x08804000 + 5857408
MIN = 6

SEC = [('.text', 0x08804040, 3258372), ('.rodata', 0x08B297C0, 2195504),
       ('.data', 0x08D41800, 310372), ('.rodata.sceResident', 0x08B21570, 31748)]


def secao(va):
    for n, a, s in SEC:
        if a <= va < a + s:
            return n
    return '?'


def classe(c):
    o = ord(c)
    if c in '\n\t':
        return 'ctl_ok'
    if o < 0x20 or o == 0x7F:
        return 'ctl_mau'
    if o < 0x7F:
        return 'ascii'
    if 0x3040 <= o <= 0x30FF:
        return 'kana'
    if 0x4E00 <= o <= 0x9FFF:
        return 'kanji'
    if 0x3000 <= o <= 0x303F or 0xFF01 <= o <= 0xFF60:
        return 'pontfw'
    if 0x25A0 <= o <= 0x25FF or 0x2190 <= o <= 0x21FF:
        return 'simbolo'
    return 'outro'


def texto(d, va):
    """Devolve (str, bytes) se o vaddr aponta para string plausivel, senao None."""
    p = va - DELTA
    if not (0 <= p < ELF_FIM) or d[p] == 0:
        return None
    z = d.find(b'\x00', p)
    if z < 0 or z - p > 1000:
        return None
    b = d[p:z]
    try:
        s = b.decode('euc_jp')
    except UnicodeDecodeError:
        return None
    cs = collections.Counter(classe(c) for c in s)
    if cs['ctl_mau'] or cs['outro']:
        return None
    return s, b


def jp(s):
    cs = collections.Counter(classe(c) for c in s)
    return cs['kana'] + cs['kanji'] + cs['pontfw'] > 0


def main():
    d = open(sys.argv[1], 'rb').read()[:ELF_FIM]
    minc = int(sys.argv[2]) if len(sys.argv) > 2 else MIN
    # zonas onde tabela pode morar
    zonas = [('.data', 0x08D41800, 310372), ('.rodata', 0x08B297C0, 2195504)]
    tabelas = []
    for _, z_va, z_sz in zonas:
        va = z_va
        corrida = []
        while va < z_va + z_sz - 3:
            w, = struct.unpack_from('<I', d, va - DELTA)
            t = texto(d, w) if VA_LO <= w < VA_HI else None
            if t:
                corrida.append((va, w, t[0], t[1]))
            else:
                if len(corrida) >= minc:
                    tabelas.append(corrida)
                corrida = []
            va += 4
        if len(corrida) >= minc:
            tabelas.append(corrida)

    print(f'tabelas com >= {minc} entradas consecutivas: {len(tabelas)}')
    tot = sum(len(t) for t in tabelas)
    alvos = {c[1] for t in tabelas for c in t}
    jps = {c[1] for t in tabelas for c in t if jp(c[2])}
    print(f'entradas somadas: {tot}   strings distintas: {len(alvos)}   '
          f'com japones: {len(jps)}')
    print()
    print(f"{'tabela em':<12}{'n':>5}  {'secao':<9} primeira -> ultima")
    for t in sorted(tabelas, key=lambda t: -len(t)):
        n_jp = sum(1 for c in t if jp(c[2]))
        if n_jp == 0:
            continue
        p, u = t[0], t[-1]
        pr = p[2].replace('\n', ' ')[:26]
        ul = u[2].replace('\n', ' ')[:26]
        print(f'0x{t[0][0]:08X}{len(t):>5}  {secao(p[1]):<9} jp={n_jp:<5} {pr!r} -> {ul!r}')

    if len(sys.argv) > 3:
        with open(sys.argv[3], 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['tabela_va', 'idx', 'va_ponteiro', 'va_string', 'secao_string',
                        'bytes', 'jp', 'original'])
            for t in tabelas:
                for i, (vp, vs, s, b) in enumerate(t):
                    w.writerow([f'0x{t[0][0]:08X}', i, f'0x{vp:08X}', f'0x{vs:08X}',
                                secao(vs), len(b), int(jp(s)), s.replace('\n', '\\n')])
        print(f'\n-> {sys.argv[3]}')


if __name__ == '__main__':
    main()

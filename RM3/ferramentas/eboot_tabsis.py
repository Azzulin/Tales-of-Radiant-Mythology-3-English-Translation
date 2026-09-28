#!/usr/bin/env python3
"""Tabela de texto de sistema do EBOOT (P-42). Somente leitura.

A tabela vive em `.data` e e' um array contiguo de u32 com o **vaddr absoluto**
da string. Nao ha secao de relocacao no EBOOT: ele carrega em endereco fixo
(0x08804000), entao ponteiro e' palavra absoluta comum. Ver P-42.

  vaddr = offset_no_arquivo + 0x08803000   (constante, medida)

Uso: eboot_tabsis.py <eboot_dec> <ini_tabela> <n> [saida.csv]
     ini_tabela em hex (vaddr), ex. 0x08D656C0
"""
import sys, csv, struct

ELF_FIM = 5862704
DELTA = 0x08803000
VA_LO, VA_HI = 0x08804000, 0x08804000 + 5857408
NUL = b'\x00'


def off(va):
    return va - DELTA


def ler(caminho):
    return open(caminho, 'rb').read()[:ELF_FIM]


def entradas(d, ini_va, n):
    """Devolve lista de dicts: i, va_ponteiro, va_string, off, bytes, original."""
    out = []
    for i in range(n):
        vp = ini_va + i * 4
        w, = struct.unpack_from('<I', d, off(vp))
        if not (VA_LO <= w < VA_HI):
            out.append({'i': i, 'va_ponteiro': vp, 'va_string': w, 'off': None,
                        'bytes': None, 'original': None, 'erro': 'nao e ponteiro'})
            continue
        p = off(w)
        z = d.find(NUL, p)
        bruto = d[p:z]
        out.append({'i': i, 'va_ponteiro': vp, 'va_string': w, 'off': p,
                    'bytes': len(bruto), 'original': bruto, 'erro': ''})
    return out


def slot_de(d, va, nbytes):
    """Bytes graváveis in-place: original + padding de zeros seguinte, deixando um NUL."""
    p = off(va) + nbytes
    assert d[p] == 0, f'sem NUL em 0x{va:08X}+{nbytes}'
    q = p
    while q < len(d) and d[q] == 0:
        q += 1
    return (q - off(va)) - 1        # texto grafavel, sem contar o NUL final


def arena(ents):
    """Faixa contigua ocupada pelas strings destas entradas, se forem contiguas."""
    vs = sorted((e['va_string'], e['bytes']) for e in ents if e['off'] is not None)
    ini = vs[0][0]
    fim = max(v + b + 1 for v, b in vs)      # +1 do NUL
    return ini, fim, fim - ini


def main():
    d = ler(sys.argv[1])
    ini = int(sys.argv[2], 16)
    n = int(sys.argv[3])
    ents = entradas(d, ini, n)
    a_ini, a_fim, a_tam = arena(ents)
    soma = sum(e['bytes'] + 1 for e in ents if e['off'] is not None)
    print(f'entradas={n}  ok={sum(1 for e in ents if not e["erro"])}')
    print(f'arena = 0x{a_ini:08X} .. 0x{a_fim:08X}  ({a_tam} bytes)')
    print(f'soma das strings + NUL = {soma} bytes')
    print(f'folga dentro da arena = {a_tam - soma} bytes (alinhamento)')
    dup = {}
    for e in ents:
        if e['off'] is not None:
            dup.setdefault(e['va_string'], []).append(e['i'])
    comp = {v: ii for v, ii in dup.items() if len(ii) > 1}
    if comp:
        print(f'strings COMPARTILHADAS por mais de um ponteiro: {len(comp)}')
        for v, ii in comp.items():
            print(f'  0x{v:08X} <- indices {ii}')
    if len(sys.argv) > 4:
        with open(sys.argv[4], 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh)
            w.writerow(['id', 'va_ponteiro', 'va_string', 'off_arquivo', 'bytes_jp',
                        'slot_inplace', 'control_codes', 'original', 'traducao',
                        'bytes_usados', 'status', 'nota'])
            for e in ents:
                if e['off'] is None:
                    continue
                b = e['original']
                cc = []
                if b'%s' in b: cc.append('%s')
                if b'%d' in b: cc.append('%d')
                if b'\n' in b: cc.append('LF')
                if b'\t' in b: cc.append('TAB')
                w.writerow([e['i'], f'0x{e["va_ponteiro"]:08X}', f'0x{e["va_string"]:08X}',
                            e['off'], e['bytes'], slot_de(d, e['va_string'], e['bytes']),
                            ' '.join(cc), b.decode('euc_jp'), '', '', 'pendente', ''])
        print(f'-> {sys.argv[4]}')


if __name__ == '__main__':
    main()

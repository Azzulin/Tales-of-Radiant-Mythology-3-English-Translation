#!/usr/bin/env python3
"""Build: reempacota a arena de um bloco do EBOOT e reescreve a tabela de ponteiros.

Uso: eboot_build.py <limpo> <lote.csv> <saida.bin> [--aplicar]

DRY-RUN por padrao (H: dry-run e backup automatico). Sem --aplicar nao escreve
nada e so relata. Escreve SEMPRE em arquivo novo — nunca no LIMPO.

Ver P-42.4 (o metodo) e P-43 (este bloco).
"""
import sys, csv, struct, hashlib, shutil, os

ELF_FIM = 5862704
DELTA = 0x08803000
PAD = b'\x00'          # byte de padding medido na arena original (P-42.4)


def main():
    limpo, lote, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    aplicar = '--aplicar' in sys.argv

    raw = bytearray(open(limpo, 'rb').read())
    n_arquivo = len(raw)
    print(f'LIMPO: {n_arquivo} bytes  sha256={hashlib.sha256(raw).hexdigest()[:16]}')
    assert raw[:4] == b'\x7fELF', 'LIMPO nao e ELF'

    rs = list(csv.DictReader(open(lote, encoding='utf-8')))
    print(f'lote: {len(rs)} linhas')

    # --- arena, medida do proprio lote ---
    vas = [int(r['va_string'], 16) for r in rs]
    tam = [int(r['bytes_jp']) for r in rs]
    a_ini = min(vas)
    a_fim = max(v + t + 1 for v, t in zip(vas, tam))
    a_tam = a_fim - a_ini
    print(f'arena 0x{a_ini:08X}..0x{a_fim:08X} = {a_tam} bytes')

    # --- fronteira: nenhuma string de FORA do lote pode estar na arena ---
    do_lote = set(vas)
    intruso = []
    p = a_ini - DELTA
    # varre toda palavra do arquivo procurando ponteiro para dentro da arena
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if a_ini <= w < a_fim and w not in do_lote:
            intruso.append((q + DELTA, w))
    if intruso:
        print(f'RECUSADO: {len(intruso)} ponteiros de fora do lote apontam para dentro da arena')
        for vp, w in intruso[:10]:
            print(f'  0x{vp:08X} -> 0x{w:08X}')
        return 1
    print('fronteira: 0 ponteiros externos apontam para dentro da arena  OK')

    # --- ponteiros do lote: cada um referenciado exatamente uma vez, e de onde ---
    esperado = {int(r['va_ponteiro'], 16): int(r['va_string'], 16) for r in rs}
    for vp, vs in esperado.items():
        w, = struct.unpack_from('<I', raw, vp - DELTA)
        assert w == vs, f'0x{vp:08X} aponta para 0x{w:08X}, lote diz 0x{vs:08X}'
    print(f'tabela: {len(esperado)} ponteiros conferem com o lote  OK')

    # --- monta o novo pool ---
    novo = bytearray()
    destino = {}
    for r in rs:
        en = r['traducao'].replace('\\n', '\n').encode('ascii')
        destino[int(r['va_ponteiro'], 16)] = a_ini + len(novo)
        novo += en + b'\x00'
    print(f'pool novo: {len(novo)} bytes em {a_tam} disponiveis  '
          f'-> {"CABE" if len(novo) <= a_tam else "ESTOURA"} (folga {a_tam-len(novo):+d})')
    if len(novo) > a_tam:
        return 1
    novo += PAD * (a_tam - len(novo))
    assert len(novo) == a_tam

    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    # --- escreve ---
    out = bytearray(raw)
    out[a_ini - DELTA:a_fim - DELTA] = novo
    for vp, vs in destino.items():
        struct.pack_into('<I', out, vp - DELTA, vs)
    assert len(out) == n_arquivo, f'tamanho mudou: {len(out)} != {n_arquivo}'

    with open(saida, 'wb') as fh:
        fh.write(out)
    print(f'\n-> {saida}  {len(out)} bytes  sha256={hashlib.sha256(out).hexdigest()[:16]}')

    # --- diff de bytes ---
    dif = [i for i in range(n_arquivo) if raw[i] != out[i]]
    faixas = []
    for i in dif:
        if faixas and i == faixas[-1][1] + 1:
            faixas[-1][1] = i
        else:
            faixas.append([i, i])
    print(f'\nDIFF: {len(dif)} bytes diferentes em {len(faixas)} faixas')
    for a, b in faixas:
        va = a + DELTA
        qual = 'arena (.rodata)' if a_ini <= va < a_fim else 'tabela (.data)'
        print(f'  0x{a:06X}..0x{b:06X}  vaddr 0x{va:08X}  {b-a+1:>5} B  {qual}')
    fora = [i for i in dif if not (a_ini - DELTA <= i < a_fim - DELTA)
            and not any(vp - DELTA <= i < vp - DELTA + 4 for vp in destino)]
    print(f'bytes alterados FORA da arena e da tabela: {len(fora)}  '
          f'{"OK" if not fora else "PROBLEMA"}')
    return 0 if not fora else 1


if __name__ == '__main__':
    sys.exit(main())

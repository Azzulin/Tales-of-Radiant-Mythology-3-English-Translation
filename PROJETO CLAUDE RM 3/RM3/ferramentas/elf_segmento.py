#!/usr/bin/env python3
"""Segmento de transbordo do EBOOT (P-91): um 2o PT_LOAD logo depois do `.bss`.

O EBOOT e' um ELF estatico (`ET_EXEC`, base fixa) com UM `PT_LOAD` e 39 slots
vazios na tabela de program headers. A imagem termina em `0x099BF354` (fim do
`.bss`) e nenhum codigo do jogo conhece a memoria depois disso (P-91: 0 pares
lui/lo, 0 literais). Um segundo `PT_LOAD` em `SEG_VA` faz o carregador reservar
e preencher essa memoria junto com o resto da imagem; o texto que nao cabe nas
arenas mora la, e os ponteiros do lote passam a apontar para la.

No arquivo, os dados do segmento vao depois de tudo o que o ELF ja tinha
(incluindo a cauda de 336 B do dump, P-41.2), num offset alinhado a pagina, com
`p_offset % p_align == p_vaddr % p_align` como o carregador exige.

Biblioteca:
  acrescenta(raw, dados)  -> bytes do ELF com o segmento (raw nao muda)
  fileoff(d, va)          -> offset no arquivo de um VA, em qualquer segmento
  confere(d, limpo)       -> lista de problemas estruturais ([] = ok)
  segmento(d)             -> (va, off, tamanho) do transbordo, ou None

Linha de comando (so' le):
  elf_segmento.py <eboot.bin>
"""
import sys, struct

SEG_VA = 0x099C0000          # fim do .bss (0x099BF354) arredondado a 64 KB
PAGINA = 0x1000
PT_LOAD = 1
PF_R, PF_W = 4, 2
MAX_PADRAO = 64 * 1024       # teto do transbordo; o custo e' RAM livre (P-91)
OFF_PHNUM = 0x2C


def _phdrs(d):
    phoff, = struct.unpack_from('<I', d, 0x1C)
    phent, phnum = struct.unpack_from('<HH', d, 0x2A)
    return phoff, phent, phnum, [struct.unpack_from('<8I', d, phoff + i * phent)
                                 for i in range(phnum)]


def acrescenta(raw, dados, va=SEG_VA):
    phoff, phent, phnum, ph = _phdrs(raw)
    if phnum != 1:
        raise ValueError('o ELF de entrada tem %d PT_LOAD; esperado 1 (o LIMPO)' % phnum)
    t, off0, va0, pa0, fs0, ms0, fl0, al0 = ph[0]
    if va < va0 + ms0:
        raise ValueError('segmento novo em 0x%08X cai dentro da imagem (fim 0x%08X)'
                         % (va, va0 + ms0))
    if va % PAGINA:
        raise ValueError('VA do segmento nao e alinhado a pagina')
    slot = phoff + phnum * phent
    if any(raw[slot:slot + phent]):
        raise ValueError('slot de program header livre nao esta zerado')
    off = -(-len(raw) // PAGINA) * PAGINA
    corpo = bytes(dados) + b'\x00' * (-len(dados) % 16)
    out = bytearray(raw) + b'\x00' * (off - len(raw)) + corpo
    struct.pack_into('<8I', out, slot, PT_LOAD, off, va, va, len(corpo), len(corpo),
                     PF_R | PF_W, PAGINA)
    struct.pack_into('<H', out, OFF_PHNUM, 2)
    return bytes(out)


def segmento(d):
    _, _, phnum, ph = _phdrs(d)
    if phnum < 2:
        return None
    t, off, va, pa, fs, ms, fl, al = ph[1]
    return va, off, fs


def fileoff(d, va):
    _, _, _, ph = _phdrs(d)
    for t, off, v, pa, fs, ms, fl, al in ph:
        if t == PT_LOAD and v <= va < v + fs:
            return off + (va - v)
    raise ValueError('VA 0x%08X fora de qualquer segmento com dados no arquivo' % va)


def bytes_do_cabecalho(d):
    """Offsets do arquivo que o segmento novo muda no cabecalho (e_phnum + phdr 1)."""
    phoff, phent, _, _ = _phdrs(d)
    return set(range(OFF_PHNUM, OFF_PHNUM + 2)) | set(range(phoff + phent, phoff + 2 * phent))


def confere(d, limpo=None, maximo=MAX_PADRAO):
    erros = []
    phoff, phent, phnum, ph = _phdrs(d)
    if phnum != 2:
        return ['e_phnum = %d, esperado 2' % phnum]
    t0, off0, va0, pa0, fs0, ms0, fl0, al0 = ph[0]
    t, off, va, pa, fs, ms, fl, al = ph[1]
    if t != PT_LOAD:
        erros.append('phdr 1 nao e PT_LOAD')
    if va < va0 + ms0:
        erros.append('segmento 1 sobrepoe a imagem (incluindo .bss)')
    if off % al != va % al:
        erros.append('p_offset %% p_align != p_vaddr %% p_align')
    if fs != ms:
        erros.append('filesz != memsz no transbordo')
    if off < off0 + fs0 or off + fs != len(d):
        erros.append('dados do segmento fora do lugar no arquivo')
    if fs > maximo:
        erros.append('transbordo de %d B passa do teto de %d B' % (fs, maximo))
    if va + ms > 0x0A000000:
        erros.append('segmento passa do fim da memoria de usuario')
    if limpo is not None:
        n = len(limpo)
        if len(d) < n:
            erros.append('arquivo menor que o LIMPO')
        if d[:4] != limpo[:4] or ph[0] != _phdrs(limpo)[3][0]:
            erros.append('phdr 0 ou magic mudou')
        if any(d[n:off]):
            erros.append('preenchimento entre o fim do LIMPO e o segmento nao e zero')
    return erros


def main():
    d = open(sys.argv[1], 'rb').read()
    s = segmento(d)
    if not s:
        print('%s: sem segmento de transbordo (1 PT_LOAD)' % sys.argv[1])
        return 0
    va, off, n = s
    print('transbordo: VA 0x%08X..0x%08X, offset 0x%X, %d B' % (va, va + n, off, n))
    e = confere(d)
    print('estrutura: %s' % ('ok' if not e else '; '.join(e)))
    return 1 if e else 0


if __name__ == '__main__':
    sys.exit(main())

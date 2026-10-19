#!/usr/bin/env python3
"""ASCII -> caracteres de largura dupla em EUC-JP, para telas que so' desenham
caractere de 2 bytes (P-85).

A tela de Sinopse desenha o ingles em ASCII como kanji sem sentido: o original
dela (`v2069`/`v2070`) nao tem um unico byte ASCII no texto, so' caractere de
2 bytes e codigo de controle. Converter `A` em `Ａ` (a3c1) resolve a exibicao ao
custo de 1 byte a mais por caractere.

Preserva sem tocar: o codigo de cor `0x13 RR GG BB` (P-29), o fecho `0x14`, todo
caractere EUC-JP que ja' e' de 2 bytes (inclusive o marcador `○○`) e os de 3
bytes (`0x8F`), e qualquer outro byte de controle.

Somente biblioteca. Uso: `para_largura_dupla(linha_bytes) -> bytes`.
"""

# os quatro que nao tem forma de largura dupla em JIS X 0208 viram o equivalente
# tipografico mais proximo
TROCA = {'"': '”', "'": '’', '-': '−', '~': '〜'}
ESPACO = '　'


def caractere(o):
    c = chr(o)
    if o == 0x20:
        w = ESPACO
    elif c in TROCA:
        w = TROCA[c]
    else:
        w = chr(o + 0xFEE0)
    return w.encode('euc_jp')


TABELA = {o: caractere(o) for o in range(0x20, 0x7F)}


def para_largura_dupla(linha):
    out = bytearray()
    i, n = 0, len(linha)
    while i < n:
        c = linha[i]
        if c == 0x13:                       # cor: 0x13 + 3 bytes de RGB
            out += linha[i:i + 4]
            i += 4
        elif c == 0x8F:                     # EUC-JP de 3 bytes
            out += linha[i:i + 3]
            i += 3
        elif c >= 0x80:                     # EUC-JP de 2 bytes
            out += linha[i:i + 2]
            i += 2
        elif c in TABELA:
            out += TABELA[c]
            i += 1
        else:                               # 0x14 e outros controles
            out.append(c)
            i += 1
    return bytes(out)


def tem_ascii(linha):
    return para_largura_dupla(linha) != linha

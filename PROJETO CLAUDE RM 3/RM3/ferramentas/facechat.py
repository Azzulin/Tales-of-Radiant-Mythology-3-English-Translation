#!/usr/bin/env python3
"""Formato FaceChat — cenas de dialogo do RM3 (arquivos .scr). Ver P-21.

Os .scr vivem dentro de um EZBIND e estao **gzip** (com FNAME). Descomprimidos:

    0x00  char[8]  "FaceChat"
    0x08  u16      A           — nao identificado
    0x0A  u16      n_strings
    0x0C  u16      n_tokens    — tamanho do stream de comandos, em u16
    0x0E  u16      0xFFFF
    0x10  u16[n_tokens]        stream de comandos
          u16[n_strings]       tabela de offsets, **relativa ao fim desta tabela**
          bloco de strings     EUC-JP, terminadas em NUL

offset[0] e' sempre 0. O stream de comandos referencia a fala por **indice**,
nao por offset — logo **nao ha limite de bytes por fala**. O unico teto e' o
u16 da tabela: o bloco de strings de uma cena nao pode passar de 65.535 bytes.

Encoding: **EUC-JP** (nao Shift-JIS — o .txz e' Shift-JIS; ver P-22).
Quebra de linha: `\\r\\n` real (0x0D 0x0A), nao a sequencia literal do .txz.
"""
import struct

ENC = 'euc_jp'
MAGIC = b'FaceChat'


def parse(data: bytes):
    if data[:8] != MAGIC:
        raise ValueError('sem magic FaceChat')
    a, n_str, n_tok, term = struct.unpack_from('<4H', data, 8)
    tok_end = 0x10 + n_tok * 2
    tbl_end = tok_end + n_str * 2
    if term != 0xFFFF:
        raise ValueError(f'campo 0x0e = {term:#x}, esperado 0xffff')
    if tbl_end > len(data):
        raise ValueError('tabela de offsets fora do arquivo')
    offs = list(struct.unpack_from(f'<{n_str}H', data, tok_end)) if n_str else []
    if offs and offs[0] != 0:
        raise ValueError(f'offset[0] = {offs[0]:#x}, esperado 0')
    if any(offs[i] > offs[i + 1] for i in range(len(offs) - 1)):
        raise ValueError('offsets nao crescentes')
    strings = []
    for i, o in enumerate(offs):
        start = tbl_end + o
        end = data.find(b'\x00', start)
        if end < 0:
            raise ValueError(f'string {i} sem terminador')
        strings.append(data[start:end])
    return {'a': a, 'n_tok': n_tok, 'tokens': data[0x10:tok_end],
            'tbl_end': tbl_end, 'strings': strings, 'tail': data[tbl_end + (offs[-1] if offs else 0):]}


def build(parsed):
    ss = parsed['strings']
    body = bytearray()
    offs = []
    for s in ss:
        offs.append(len(body))
        body += s + b'\x00'
    if offs and offs[-1] > 0xFFFF:
        raise ValueError('bloco de strings passou de 65535 B — a tabela e u16')
    out = bytearray(MAGIC)
    out += struct.pack('<4H', parsed['a'], len(ss), parsed['n_tok'], 0xFFFF)
    out += parsed['tokens']
    for o in offs:
        out += struct.pack('<H', o)
    out += body
    return bytes(out)


def round_trip_ok(data: bytes) -> bool:
    try:
        return build(parse(data)) == data
    except Exception:
        return False

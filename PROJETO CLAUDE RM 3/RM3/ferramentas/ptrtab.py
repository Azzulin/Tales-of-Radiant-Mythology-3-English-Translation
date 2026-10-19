#!/usr/bin/env python3
"""Formato PTRTAB — tabela de ponteiros u32 + bloco de strings. Ver P-25.

    u32       count
    u32[count] offsets, relativos ao FIM desta tabela
    bloco de strings, terminadas em NUL

Usado por `CharGuideTextCName.bin`, `CharGuideTextORG.bin`, `CharGuideTextTOW3.bin`.
Encoding: **EUC-JP**. Quebra de linha: `\\n` real (0x0A) — nem CRLF (.scr) nem
a sequencia literal de 2 bytes (.txz). Tres convencoes no mesmo jogo.

offset[0] == 0. Nao comprimido.
"""
import struct

ENC = 'euc_jp'


def parse(data: bytes):
    count = struct.unpack_from('<I', data, 0)[0]
    tbl_end = 4 + count * 4
    if count == 0 or tbl_end > len(data):
        raise ValueError(f'count implausivel: {count}')
    offs = list(struct.unpack_from(f'<{count}I', data, 4))
    if offs[0] != 0:
        raise ValueError(f'offset[0] = {offs[0]:#x}, esperado 0')
    if any(offs[i] > offs[i + 1] for i in range(count - 1)):
        raise ValueError('offsets nao crescentes')
    out = []
    for i, o in enumerate(offs):
        a = tbl_end + o
        e = data.find(b'\x00', a)
        if e < 0:
            raise ValueError(f'string {i} sem terminador')
        out.append(data[a:e])
    return {'count': count, 'tbl_end': tbl_end, 'strings': out,
            'tail': data[tbl_end + offs[-1] + len(out[-1]) + 1:]}


def build(parsed):
    ss = parsed['strings']
    body = bytearray()
    offs = []
    for s in ss:
        offs.append(len(body))
        body += s + b'\x00'
    out = bytearray(struct.pack('<I', len(ss)))
    for o in offs:
        out += struct.pack('<I', o)
    out += body + parsed.get('tail', b'')
    return bytes(out)


def round_trip_ok(data: bytes) -> bool:
    try:
        return build(parse(data)) == data
    except Exception:
        return False

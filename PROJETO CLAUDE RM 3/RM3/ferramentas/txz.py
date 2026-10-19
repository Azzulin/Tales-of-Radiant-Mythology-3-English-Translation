#!/usr/bin/env python3
"""Formato TXZ — banco de texto do RM3 (ver P-17).

Arquivo gzip (com FNAME) cujo conteudo e':

    u32 count
    count x { u32 id ; u32 offset }        <- tabela de ponteiros
    bloco de strings

A string i vai de offset[i] ate offset[i+1]; a ultima vai ate o fim do arquivo.
**Nao ha terminador e nao ha folga**: o bloco e' exatamente a soma das strings.
Encoding: Shift-JIS. Control codes: "\\n" literal (0x5C 0x6E) e tags entre
colchetes em japones, ex. "[指定色１]" / "[指定色戻し]".

parse() -> dict; build() -> bytes. build(parse(x)) == x para arquivo intacto
(garantido por round_trip_ok).
"""
import struct

ENC = 'shift_jis'


def parse(data: bytes):
    count = struct.unpack_from('<I', data, 0)[0]
    tbl_end = 4 + count * 8
    if count == 0 or tbl_end > len(data):
        raise ValueError(f'count implausivel: {count}')
    recs = [struct.unpack_from('<II', data, 4 + i * 8) for i in range(count)]
    offs = [o for _, o in recs]
    if offs[0] != tbl_end:
        raise ValueError(f'tabela termina em 0x{tbl_end:x} mas offset[0]=0x{offs[0]:x}')
    if any(offs[i] > offs[i + 1] for i in range(count - 1)):
        raise ValueError('offsets nao crescentes')
    if offs[-1] > len(data):
        raise ValueError('ultimo offset fora do arquivo')
    ends = offs[1:] + [len(data)]
    strings = [{'i': i, 'id': recs[i][0], 'off': offs[i], 'bytes': ends[i] - offs[i],
                'raw': data[offs[i]:ends[i]]} for i in range(count)]
    return {'count': count, 'tbl_end': tbl_end, 'strings': strings}


def build(parsed):
    ss = parsed['strings']
    out = bytearray(struct.pack('<I', len(ss)))
    off = 4 + len(ss) * 8
    tbl = bytearray()
    body = bytearray()
    for s in ss:
        tbl += struct.pack('<II', s['id'], off)
        body += s['raw']
        off += len(s['raw'])
    out += tbl + body
    return bytes(out)


def round_trip_ok(data: bytes) -> bool:
    return build(parse(data)) == data


def decode(raw: bytes) -> str:
    return raw.decode(ENC)


def encode(text: str) -> bytes:
    return text.encode(ENC)

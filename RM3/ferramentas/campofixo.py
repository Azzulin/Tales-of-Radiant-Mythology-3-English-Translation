#!/usr/bin/env python3
"""Formato CAMPOFIXO — banco de titulos com campo de tamanho fixo. Ver P-27.

Usado pela entrada v2063 do bdi (titulos de skit/evento):

    registro de 68 bytes, repetido:
       +0   u32   id  (observado: (i+1) * 0x5001 — preservar verbatim)
       +4   char[64]  string EUC-JP terminada em NUL, resto preenchido com 0x00

**O orçamento e' o campo:** 64 bytes por titulo, terminador incluido, ou seja 63
bytes uteis. O maior original usa 32 — sobra real. Mudar tamanho **nao** move nada
e **nao** exige recalcular ponteiro: o campo e' fixo.
"""
import struct

ENC = 'euc_jp'
REC = 68
CAMPO = 64


def parse(data: bytes):
    util = len(data.rstrip(b'\x00'))
    n = util // REC
    if n == 0:
        raise ValueError('nenhum registro')
    regs = []
    for i in range(n):
        o = i * REC
        idv = struct.unpack_from('<I', data, o)[0]
        fld = data[o + 4:o + REC]
        z = fld.find(b'\x00')
        if z < 0:
            raise ValueError(f'registro {i} sem NUL dentro do campo de {CAMPO} B')
        regs.append({'i': i, 'id': idv, 'raw': fld[:z]})
    return {'n': n, 'regs': regs, 'cauda': data[n * REC:]}


def build(parsed):
    out = bytearray()
    for r in parsed['regs']:
        if len(r['raw']) >= CAMPO:
            raise ValueError(f"registro {r['i']}: {len(r['raw'])} B >= campo de {CAMPO}")
        out += struct.pack('<I', r['id'])
        out += r['raw'] + b'\x00' * (CAMPO - len(r['raw']))
    return bytes(out) + parsed.get('cauda', b'')


def round_trip_ok(data: bytes) -> bool:
    try:
        return build(parse(data)) == data
    except Exception:
        return False

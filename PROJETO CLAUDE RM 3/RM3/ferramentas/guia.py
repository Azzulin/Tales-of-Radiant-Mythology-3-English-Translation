#!/usr/bin/env python3
"""Formato GUIA — guia/tutorial do RM3 (entrada v2065 do bdi). Ver P-28.

    0x00  u32   count (211)
    ...         (cabecalho de 0x3c bytes, campos nao identificados)
    0x3c  count x registro de 36 bytes:
             +0  u32 off_titulo  (offset ABSOLUTO no arquivo)
             +4  u32 off_corpo   (offset ABSOLUTO no arquivo)
             +8  u32 id
             +12..+32  cinco u32 nao identificados — preservar verbatim
    pool de strings EUC-JP terminadas em NUL, alinhadas a 4 bytes

**Parcialmente decifrado:** os offsets sao absolutos e validados; os campos
+12..+32 do registro e a regiao entre o fim da tabela e o pool nao foram
identificados. Por isso este modulo **le e nao reescreve** — nao ha `build()`
ate a estrutura fechar.
"""
import struct

ENC = 'euc_jp'
REC = 36
TAB = 0x3c


def parse(data: bytes):
    count = struct.unpack_from('<I', data, 0)[0]
    if not (0 < count < 10000) or TAB + count * REC > len(data):
        raise ValueError(f'count implausivel: {count}')
    regs = []
    for i in range(count):
        o = TAB + i * REC
        campos = struct.unpack_from('<9I', data, o)
        t_off, c_off, idv = campos[0], campos[1], campos[2]
        def s(a):
            if not (0 <= a < len(data)):
                return None
            z = data.find(b'\x00', a)
            return data[a:z] if z >= 0 else None
        regs.append({'i': i, 'id': idv, 't_off': t_off, 'c_off': c_off,
                     'titulo': s(t_off), 'corpo': s(c_off), 'resto': campos[3:]})
    return {'count': count, 'regs': regs}

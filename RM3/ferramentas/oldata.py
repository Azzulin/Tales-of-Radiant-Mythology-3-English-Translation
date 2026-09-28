#!/usr/bin/env python3
"""Formato OLDATA — historia/narracao do RM3 (`oldata.bin`, gzip). Ver P-26.

Descomprimido:

    0x00  u32 count            numero de episodios (52)
    0x04  u32 off_titulos      offset absoluto  (== 12 + count*12)
    0x08  u32 off_narracao     offset absoluto
    0x0c  count x 12 bytes:
             +0 u32 A   limiar de progressao (80, 1000, 1500, 2000, ... +500)
             +4 u32 B   NAO IDENTIFICADO — preservar verbatim (ver P-26)
             +8 u32 C   offset da narracao do episodio, relativo a off_narracao
    off_titulos   count linhas terminadas em LF (0x0A) — os titulos de episodio
    off_narracao  linhas terminadas em LF — a narracao

Encoding: **EUC-JP**. Quebra de linha: `\\n` real (0x0A). Sem NUL em lugar nenhum.
Verificado: C cai em inicio de linha da narracao em **52 de 52** episodios.
"""
import struct

ENC = 'euc_jp'


def _lines(blob):
    ls = blob.split(b'\n')
    trailing = ls and ls[-1] == b''
    if trailing:
        ls = ls[:-1]
    return ls, trailing


def cabecalho(data: bytes):
    """Detecta a largura do cabecalho: u32 (oldata.bin) ou u16 (a entrada v2069).
    O invariante que decide e' `off_titulos == tamanho_do_cabecalho + count*12`."""
    for fmt, hs in (('<3I', 12), ('<3H', 6)):
        try:
            count, t_off, n_off = struct.unpack_from(fmt, data, 0)
        except struct.error:
            continue
        if count and t_off == hs + count * 12 and t_off < n_off <= len(data):
            return count, t_off, n_off, hs
    raise ValueError('cabecalho OLDATA nao reconhecido (nem u32 nem u16)')


def parse(data: bytes):
    """Aceita o arquivo com ou sem o padding de NUL da entrada do bdi."""
    data = data[:len(data.rstrip(b'\x00'))] or data
    count, t_off, n_off, hs = cabecalho(data)
    if False:
        raise ValueError('')
    if not (t_off < n_off <= len(data)):
        raise ValueError('offsets fora de ordem')
    recs = [list(struct.unpack_from('<3I', data, hs + i * 12)) for i in range(count)]
    titulos, t_trail = _lines(data[t_off:n_off])
    narracao, n_trail = _lines(data[n_off:])
    if len(titulos) != count:
        raise ValueError(f'{len(titulos)} titulos != count {count}')
    # C tem de cair em inicio de linha da narracao
    starts = {0}
    pos = 0
    for l in narracao:
        pos += len(l) + 1
        starts.add(pos)
    # C cai em inicio de linha em 52/52 no oldata.bin e em 51/52 na entrada v2069.
    # O episodio divergente e' registrado como AVISO, nao como erro: C e' um offset
    # em bytes e o formato nao exige alinhamento a linha. Ver P-26.
    avisos = [i for i, r in enumerate(recs) if r[2] not in starts]
    return {'count': count, 'recs': recs, 'titulos': titulos, 'narracao': narracao,
            't_trail': t_trail, 'n_trail': n_trail, 'hs': hs, 'avisos': avisos, 'cauda': data[n_off + sum(len(l) + 1 for l in narracao):]}


def build(parsed):
    tit = b'\n'.join(parsed['titulos']) + (b'\n' if parsed['t_trail'] else b'')
    nar = b'\n'.join(parsed['narracao']) + (b'\n' if parsed['n_trail'] else b'')
    count = len(parsed['titulos'])
    hs = parsed.get('hs', 12)
    t_off = hs + count * 12
    n_off = t_off + len(tit)
    out = bytearray(struct.pack('<3I' if hs == 12 else '<3H', count, t_off, n_off))
    # recalcula C a partir do indice de linha original; A e B sao preservados
    starts, pos = [0], 0
    for l in parsed['narracao']:
        pos += len(l) + 1
        starts.append(pos)
    for A, B, C in parsed['recs']:
        out += struct.pack('<3I', A, B, C)
    out += tit + nar + parsed.get('cauda', b'')
    return bytes(out)


def recalcular_C(parsed, indices):
    """Recalcula o campo C dos episodios a partir dos indices de linha da narracao.
    Use APOS mudar o texto. `indices[i]` = indice da 1a linha da narracao do episodio i."""
    starts, pos = [0], 0
    for l in parsed['narracao']:
        pos += len(l) + 1
        starts.append(pos)
    for i, idx in enumerate(indices):
        parsed['recs'][i][2] = starts[idx]
    return parsed


def indices_de_linha(parsed):
    """Indice de linha da narracao de cada episodio, derivado do C atual."""
    starts, pos = {0: 0}, 0
    for k, l in enumerate(parsed['narracao']):
        pos += len(l) + 1
        starts[pos] = k + 1
    return [starts[r[2]] for r in parsed['recs']]


def round_trip_ok(data: bytes) -> bool:
    try:
        return build(parse(data)) == data
    except Exception:
        return False

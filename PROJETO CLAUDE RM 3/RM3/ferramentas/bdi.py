#!/usr/bin/env python3
"""Leitura do indice do namco.bdi — versao correta (ver P-14).

ATENCAO: substitui o parser errado que estava em bdi_ls.py, que tratava o campo
como offset em bytes. O campo e' (flag<<31 | setor<<11 | A). Ver P-14.

  0x0000  u16[16384]   tabela hash: slot -> v   (0 = vazio)
  0x8004  base dos registros; registro v em 0x8004 + v*8
          +0 u32 = bit31 flag | bits30..11 setor (x2048) | bits10..0 campo A (nao decifrado)
          +4 u32 = chave (hash do nome)
          v = 0 e 1 sao dummies; v = 2 .. 2+count-1 sao entradas; o registro
          seguinte a ultima entrada e' a sentinela (setor = tamanho/2048)
  count   u32 em 0x8004

Somente leitura. Nunca abre a ISO para escrita.
"""
import struct

SEC = 2048
HASH_BYTES = 0x8000
REC_BASE = 0x8004


def load_index(f, base):
    """Devolve (buckets, count, entries, sentinel_off).

    entries: lista de dicts com v, sect, off, nsect, span (nsect*2048), flag, A, key.
    'span' e' o espaco reservado, NAO o tamanho exato do conteudo — o tamanho
    exato vem do proprio conteudo (o EZBIND declara; o gzip termina sozinho).
    """
    f.seek(base)
    head = f.read(HASH_BYTES + 16)
    buckets = struct.unpack_from('<16384H', head, 0)
    count = struct.unpack_from('<I', head, REC_BASE)[0]
    f.seek(base)
    raw = f.read(REC_BASE + (2 + count + 1) * 8)
    rec = []
    for v in range(2, 2 + count + 1):          # +1 = sentinela
        a, key = struct.unpack_from('<II', raw, REC_BASE + v * 8)
        rec.append({'v': v, 'flag': a >> 31, 'sect': (a >> 11) & 0xFFFFF,
                    'A': a & 0x7FF, 'key': key})
    entries = []
    for i in range(len(rec) - 1):
        e = dict(rec[i])
        e['off'] = e['sect'] * SEC
        e['nsect'] = rec[i + 1]['sect'] - e['sect']
        e['span'] = e['nsect'] * SEC
        entries.append(e)
    return buckets, count, entries, rec[-1]['sect'] * SEC


def validate(buckets, count, entries, sentinel, bdi_size):
    """Checagens que devem passar num namco.bdi intacto. Devolve lista de falhas."""
    bad = []
    if sentinel != bdi_size:
        bad.append(f'sentinela {sentinel} != tamanho {bdi_size}')
    if len(entries) != count:
        bad.append(f'{len(entries)} entradas != count {count}')
    nz = [b for b in buckets if b]
    if len(nz) != count or len(set(nz)) != count:
        bad.append(f'buckets: {len(nz)} nao-zero, {len(set(nz))} distintos, count={count}')
    if set(nz) != set(range(2, 2 + count)):
        bad.append('buckets nao cobrem exatamente v=2..count+1')
    s = [e['sect'] for e in entries]
    if any(s[i] >= s[i + 1] for i in range(len(s) - 1)):
        bad.append('setores nao estritamente crescentes')
    if any(e['nsect'] <= 0 for e in entries):
        bad.append('nsect <= 0 em alguma entrada')
    return bad


# ---------- formatos internos ----------

def parse_ezbind(f, base, off, span):
    """EZBIND (ver P-15): magic 8 B, u32 count, u32 data_off, registros de 16 B,
    pool de nomes, dados. Devolve dict ou None."""
    f.seek(base + off)
    head = f.read(16)
    if head[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', head, 8)[0]
    data_off = struct.unpack_from('<I', head, 0xc)[0]
    if not (0 < count <= 4000):
        return None
    need = 0x10 + count * 16
    f.seek(base + off)
    blob = f.read(min(span, max(need + 0x8000, 0x10000)))
    if len(blob) < need:
        return None
    files, total = [], 0
    for i in range(count):
        name_off, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        end = blob.find(b'\x00', name_off) if name_off < len(blob) else -1
        name = blob[name_off:end].decode('latin1') if end > name_off else ''
        files.append({'name': name, 'size': sz, 'data_off': do, 'key': key})
        total = max(total, do + sz)
    return {'count': count, 'data_off': data_off, 'total': total, 'files': files}


def gzip_name(f, base, off):
    """Nome original guardado no header gzip (flag FNAME 0x08)."""
    f.seek(base + off)
    h = f.read(10)
    if h[:3] != b'\x1f\x8b\x08' or not (h[3] & 0x08):
        return None
    f.seek(base + off + 10)
    chunk = f.read(256)
    end = chunk.find(b'\x00')
    return chunk[:end].decode('latin1') if end > 0 else None


MAGICS = [(b'EZBIND', 'EZBIND'), (b'NBI\x00', 'NBI'), (b'\x1f\x8b\x08', 'gzip'),
          (b'RIFF', 'RIFF'), (b'PPHD', 'PPHD'), (b'ACE0', 'ACE0'), (b'ppt\x00', 'ppt'),
          (b'BM', 'BMP'), (b'MDL\x00', 'MDL'), (b'NOD\x00', 'NOD'), (b'TXL\x00', 'TXL')]


def classify(head):
    for m, name in MAGICS:
        if head.startswith(m):
            return name
    return '?'

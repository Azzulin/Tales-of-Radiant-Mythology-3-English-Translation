#!/usr/bin/env python3
"""Extrai UMA cena .scr do namco.bdi para a memoria. Somente leitura.

Uso: import scr_get; d = scr_get.pega(iso, lba, 'mev00_010.scr')
As cenas moram em entradas gzip do bdi; algumas dentro de EZBIND aninhado (P-35).
"""
import gzip, struct, csv
from bdi import load_index

SEC = 2048


def _ezbind(blob):
    if blob[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < count <= 4000) or 0x10 + count * 16 > len(blob):
        return None
    out = []
    for i in range(count):
        no, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(b'\x00', no) if no < len(blob) else -1
        out.append((blob[no:z].decode('latin1') if z > no else '', sz, do))
    return out


def _desce(blob, alvo, prof=0):
    if prof > 5:
        return None
    if blob[:3] == b'\x1f\x8b\x08':
        try:
            blob = gzip.decompress(blob)
        except Exception:
            return None
        return _desce(blob, alvo, prof + 1)
    if blob[:8] == b'FaceChat':
        return blob
    fs = _ezbind(blob)
    if fs:
        for nome, sz, do in fs:
            if nome.lower() == alvo.lower():
                return _desce(blob[do:do + sz], alvo, prof + 1)
        return None
    return None


def pega(iso, lba, alvo, v=None):
    base = lba * SEC
    with open(iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        cands = [e for e in entries if v is None or e['v'] == v]
        for e in cands:
            f.seek(base + e['off'])
            blob = f.read(min(e['span'], 4 << 20))
            r = _desce(blob, alvo)
            if r:
                return r, e['v']
    return None, None

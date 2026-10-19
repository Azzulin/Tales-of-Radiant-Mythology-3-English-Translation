#!/usr/bin/env python3
"""Catalogo RECURSIVO do namco.bdi. Ver P-35.

Corrige o furo do bdi_catalog.py: ele nao descia nas 1.317 entradas gzip (que sao
`.arc`, ou seja EZBIND comprimido) nem no EZBIND aninhado. Os arquivos internos
delas nunca foram enumerados.

Uso: bdi_catalog2.py <iso> <lba> <size> <estado.json> <saida.csv> [segundos]

RESUMIVEL (H-15): processa entradas ate esgotar o orcamento de tempo e grava o
estado. Rode de novo ate `restam=0`. Somente leitura.

Colunas: entrada_v, profundidade, caminho, nome, tipo, tamanho, off_bdi, chave
`off_bdi` so e' valido para arquivo NAO comprimido em nivel 0 ou 1 (dentro de
EZBIND cru). Para conteudo que veio de gzip, `off_bdi` fica vazio: o dado nao
existe em lugar nenhum do disco em texto claro, so depois de descomprimir.
"""
import sys, os, csv, json, gzip, struct, time
from bdi import load_index, classify, SEC

MAXDEPTH = 5


def ezbind_files(blob):
    """Enumera (nome, tamanho, data_off) de um EZBIND ja em memoria."""
    if blob[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < count <= 4000) or 0x10 + count * 16 > len(blob):
        return None
    out = []
    for i in range(count):
        no, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(b'\x00', no) if no < len(blob) else -1
        nome = blob[no:z].decode('latin1') if z > no else ''
        out.append((nome, sz, do, key))
    return out


def gz_nome(blob):
    if blob[:3] != b'\x1f\x8b\x08' or not (blob[3] & 0x08):
        return None
    z = blob.find(b'\x00', 10)
    return blob[10:z].decode('latin1') if z > 10 else None


def walk(blob, caminho, v, depth, off_base, rows, stat):
    """Emite uma linha por arquivo logico; desce em gzip e EZBIND."""
    if depth > MAXDEPTH:
        stat['profundidade_estourada'] += 1
        return
    comprimido = False
    nome_gz = gz_nome(blob)
    if blob[:3] == b'\x1f\x8b\x08':
        try:
            blob = gzip.decompress(blob)
            comprimido = True
            off_base = None                    # o dado cru nao existe no disco
        except Exception:
            stat['gzip_ilegivel'] += 1
            rows.append([v, depth, caminho, nome_gz or '', 'gzip(ilegivel)',
                         len(blob), off_base if off_base is not None else '', ''])
            return
    fs = ezbind_files(blob)
    if fs is not None:
        stat['ezbind'] += 1
        for nome, sz, do, key in fs:
            sub = blob[do:do + sz]
            filho = f'{caminho}/{nome}' if caminho else nome
            if sub[:3] == b'\x1f\x8b\x08' or sub[:6] == b'EZBIND':
                walk(sub, filho, v, depth + 1,
                     None if off_base is None else off_base + do, rows, stat)
            else:
                rows.append([v, depth + 1, filho, nome, classify(sub[:16]), sz,
                             '' if off_base is None else off_base + do, f'{key:08x}'])
                stat['folhas'] += 1
        return
    tipo = classify(blob[:16])
    if comprimido:
        tipo = f'gzip>{tipo}'
    rows.append([v, depth, caminho, nome_gz or (caminho.split('/')[-1] if caminho else ''),
                 tipo, len(blob), '' if off_base is None else off_base, ''])
    stat['folhas'] += 1


def main():
    iso, lba, size, st_path, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    budget = float(sys.argv[6]) if len(sys.argv) > 6 else 155.0
    base = lba * SEC
    t0 = time.time()
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'i': 0, 'stat': {}}
    stat = {'ezbind': 0, 'folhas': 0, 'gzip_ilegivel': 0, 'profundidade_estourada': 0}
    for k, v in st['stat'].items():
        stat[k] = v
    modo = 'a' if st['i'] else 'w'
    rows = []
    with open(iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        while st['i'] < len(entries) and time.time() - t0 < budget:
            e = entries[st['i']]
            st['i'] += 1
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            walk(blob, '', e['v'], 0, e['off'], rows, stat)
    with open(out, modo, newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        if modo == 'w':
            w.writerow(['entrada_v', 'profundidade', 'caminho', 'nome', 'tipo',
                        'tamanho', 'off_bdi', 'chave'])
        w.writerows(rows)
    st['stat'] = stat
    json.dump(st, open(st_path, 'w'))
    restam = len(entries) - st['i']
    print(f'processadas={st["i"]}/{len(entries)}  restam={restam}  '
          f'linhas nesta chamada={len(rows)}  ({time.time()-t0:.1f}s)')
    print(f'  acumulado: folhas={stat["folhas"]} ezbind_abertos={stat["ezbind"]} '
          f'gzip_ilegivel={stat["gzip_ilegivel"]} profundidade_estourada={stat["profundidade_estourada"]}')


if __name__ == '__main__':
    main()

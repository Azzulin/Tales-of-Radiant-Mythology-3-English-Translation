#!/usr/bin/env python3
"""checa_familias3_diagnostico.py -- terceira passada: corrige uma metrica enganosa
da segunda passada e identifica o formato real de cada familia por magic/cabecalho.

Contexto: checa_familias2.py soma, para cada cadeia delimitada por NUL que contem
QUALQUER run de kana/kanji, o tamanho da CADEIA INTEIRA como "bytes_jp" -- isso
superestima brutalmente familias com cadeias grandes (ex.: .mnm, onde uma cadeia de
800+ bytes de binario e contada inteira so' porque 2 bytes no meio bateram com o
padrao Shift-JIS/EUC por acaso). Este script:

  1) Le achados/resumo de saida2.json (saida de checa_familias2.py) e recalcula um
     "bytes_jp real" = soma dos bytes dos RUNS casados em si (n_chars*2), nao da
     cadeia inteira -- metrica muito mais honesta de volume de texto.
  2) Le a ISO ('rb', somente leitura) e mostra o cabecalho/magic + entropia de
     amostras de cada familia, para identificar o formato real por trás do binario.
  3) Para .mao, conta ocorrencias do padrao float 1.0f little-endian (0000803f),
     que explica a maior parte dos "runs japoneses" como bytes de matriz/quaternion.

Uso:
  checa_familias3_diagnostico.py <iso> <lba> <size> <catalogo2.csv> <saida2.json> --ferramentas DIR
"""
import sys, os, csv, gzip, io, struct, collections, math, json

EXTS = ('zqe', 'mid', 'mao', 'mnm', 'mso')


def ezb(blob):
    if blob[:6] != b'EZBIND':
        return None
    cnt = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < cnt <= 4000) or 0x10 + cnt * 16 > len(blob):
        return None
    out = {}
    for i in range(cnt):
        no, sz, do, _k = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(b'\x00', no) if no < len(blob) else -1
        out[blob[no:z].decode('latin1') if z > no else ''] = (do, sz)
    return out


def gunz(b):
    try:
        return gzip.GzipFile(fileobj=io.BytesIO(b)).read()
    except Exception:
        return None


def resolve(f, base, porv, row):
    e = porv.get(int(row['entrada_v']))
    if not e:
        return None
    f.seek(base + e['off'])
    blob = f.read(e['span'])
    partes = row['caminho'].split('/')
    for idx, p in enumerate(partes):
        if blob[:3] == b'\x1f\x8b\x08':
            d = gunz(blob)
            if d is None:
                return None
            blob = d
        if idx == len(partes) - 1:
            break
        t = ezb(blob)
        if not t or partes[idx + 1] not in t:
            return None
        do, sz = t[partes[idx + 1]]
        blob = blob[do:do + sz]
    tam = int(row['tamanho'])
    return blob[:tam] if len(blob) >= tam else blob


def entropia(b):
    if not b:
        return 0.0
    h = collections.Counter(b)
    n = len(b)
    return -sum((c / n) * math.log2(c / n) for c in h.values())


def main():
    iso, lba, size, cat, saida2 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    sys.path.insert(0, sys.argv[sys.argv.index('--ferramentas') + 1])
    from bdi import load_index, validate
    SEC = 2048
    base = lba * SEC

    print('===== metrica corrigida: bytes REALMENTE casados como JP (soma dos runs, nao a cadeia NUL inteira) =====')
    d = json.load(open(saida2, encoding='utf-8'))
    ach, res = d['achados'], d['resumo']
    for e in list(EXTS) + ['scr']:
        items = [a for a in ach if a['ext'] == e]
        run_bytes = 0
        for a in items:
            for _s, n in (a.get('sjis') or []):
                run_bytes += n * 2
            for _s, n in (a.get('euc') or []):
                run_bytes += n * 2
        tot = res[e]['bytes_lidos']
        chain_bytes = res[e]['bytes_das_cadeias_com_jp']
        print('%-5s bytes_total=%9d  bytes_cadeia_inteira_flagueada=%9d (%5.2f%%)   '
              'bytes_REAIS_em_runs_jp(amostrados,max400)=%6d (%6.3f%%)' % (
                  e, tot, chain_bytes, 100 * chain_bytes / tot if tot else 0,
                  run_bytes, 100 * run_bytes / tot if tot else 0))

    print('\n===== headers/magic + entropia por amostra =====')
    f = open(iso, 'rb')                       # SOMENTE LEITURA
    buckets, count, entries, sentinel = load_index(f, base)
    bad = validate(buckets, count, entries, sentinel, size)
    if bad:
        print('INDICE REPROVADO', bad)
        sys.exit(2)
    porv = {e['v']: e for e in entries}

    byext = collections.defaultdict(list)
    with open(cat, newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh):
            nm = row['nome'].lower()
            e = nm.rsplit('.', 1)[-1] if '.' in nm else ''
            if e in EXTS:
                byext[e].append(row)

    for e in EXTS:
        print('\n--- %s (%d no catalogo) ---' % (e, len(byext[e])))
        for row in byext[e][:4]:
            if row['off_bdi']:
                off, tam = int(row['off_bdi']), int(row['tamanho'])
                f.seek(base + off)
                b = f.read(tam)
            else:
                b = resolve(f, base, porv, row)
            if b is None:
                print('  (falhou)', row['caminho'])
                continue
            z = b.count(0)
            print('  %-40s tam=%7d entropia=%.2f %%zero=%5.1f head16=%s' % (
                row['caminho'], len(b), entropia(b), 100 * z / len(b), b[:16].hex()))

    print("\n--- mao: contagem de '0000803f' (1.0f little-endian) por arquivo amostra ---")
    for row in byext['mao'][:5]:
        off, tam = int(row['off_bdi']), int(row['tamanho'])
        f.seek(base + off)
        b = f.read(tam)
        n = b.count(bytes.fromhex('0000803f'))
        print('  %-20s tam=%6d occurrencias_1.0f=%d' % (row['caminho'], tam, n))

    f.close()


if __name__ == '__main__':
    main()

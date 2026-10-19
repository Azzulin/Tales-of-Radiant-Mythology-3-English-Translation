#!/usr/bin/env python3
"""Varredura do UNIVERSO: procura japones real em todos os arquivos logicos do bdi.

H-06 do RM2: *verifique o universo, nao a saida da ferramenta*. Esta varredura
serve para **achar candidato novo** — nunca para provar que uma frente esta limpa
(para isso, siga a tabela do proprio arquivo; ver a skill `rom-frente-limpa`).

Uso: sweep_texto.py <iso> <lba> <size> <estado.json> [segundos]

RESUMIVEL (H-15 do RM2: job destacado morre em silencio). Cada chamada processa
entradas do bdi ate esgotar o orcamento de tempo e grava o estado em disco.
Rode de novo ate `restam=0`.

Discriminador: run maximal de bytes validos no encoding, com **>= 1 kana** e
>= 6 bytes. Vale para EUC-JP e Shift-JIS, testados separadamente por arquivo.
Somente leitura.
"""
import sys, json, os, time, gzip, struct, re
from bdi import load_index, parse_ezbind, classify, SEC

KANA_JP = re.compile(r'[぀-ゟ゠-ヿ]')
KANJI = re.compile(r'[一-鿿]')


def runs(blob, enc):
    """Runs maximais decodificaveis com pelo menos um kana. Devolve (n_runs, n_bytes)."""
    n = b = 0
    i, L = 0, len(blob)
    lead2 = (lambda c: 0xa1 <= c <= 0xfe) if enc == 'euc_jp' else \
            (lambda c: 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef)
    trail = (lambda c: 0xa1 <= c <= 0xfe) if enc == 'euc_jp' else \
            (lambda c: 0x40 <= c <= 0xfc and c != 0x7f)
    while i < L:
        j = i
        while j < L:
            c = blob[j]
            if 0x20 <= c < 0x7f or c in (0x09, 0x0a, 0x0d):
                j += 1
            elif lead2(c) and j + 1 < L and trail(blob[j + 1]):
                j += 2
            else:
                break
        if j - i >= 6:
            try:
                t = blob[i:j].decode(enc)
                if KANA_JP.search(t):
                    n += 1
                    b += j - i
            except UnicodeDecodeError:
                pass
            i = j
        else:
            i += 1
    return n, b


def scan(blob):
    best = ('', 0, 0)
    for enc in ('euc_jp', 'shift_jis'):
        n, b = runs(blob, enc)
        if b > best[2]:
            best = (enc, n, b)
    return best


def main():
    iso, lba, size, st_path = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    budget = float(sys.argv[5]) if len(sys.argv) > 5 else 33.0
    base = lba * SEC
    t0 = time.time()
    st = json.load(open(st_path)) if os.path.exists(st_path) else {'i': 0, 'res': {}, 'files': {}}
    with open(iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        while st['i'] < len(entries) and time.time() - t0 < budget:
            e = entries[st['i']]
            st['i'] += 1
            f.seek(base + e['off'])
            span = f.read(e['span'])
            tipo = classify(span[:16])
            itens = []
            if tipo == 'EZBIND':
                ez = parse_ezbind(f, base, e['off'], e['span'])
                if ez:
                    for fi in ez['files']:
                        d = span[fi['data_off']:fi['data_off'] + fi['size']]
                        itens.append((fi['name'], d))
            if not itens:
                nome = ''
                if tipo == 'gzip':
                    h = span[:280]
                    if h[3] & 0x08:
                        z = h.find(b'\x00', 10)
                        nome = h[10:z].decode('latin1') if z > 10 else ''
                itens = [(nome or f'(v{e["v"]}.{tipo})', span)]
            for nome, d in itens:
                if d[:3] == b'\x1f\x8b\x08':
                    try:
                        d = gzip.decompress(d)
                    except Exception:
                        pass
                enc, nr, nb = scan(d)
                ext = nome.rsplit('.', 1)[-1].lower() if '.' in nome else '(sem)'
                k = f'{ext}|{enc or "-"}'
                r = st['res'].setdefault(k, [0, 0, 0, 0])   # arquivos, com_texto, runs, bytes
                r[0] += 1
                if nb:
                    r[1] += 1; r[2] += nr; r[3] += nb
                    st['files'][nome] = st['files'].get(nome, 0) + nb
    json.dump(st, open(st_path, 'w'))
    restam = len(entries) - st['i']
    print(f'processadas={st["i"]}/{len(entries)}  restam={restam}  ({time.time()-t0:.1f}s)')
    if restam == 0:
        print('\n--- por extensao|encoding: arquivos / com_texto / trechos / bytes ---')
        for k, v in sorted(st['res'].items(), key=lambda kv: -kv[1][3]):
            if v[3]:
                print(f'  {k:<18} {v[0]:>7} {v[1]:>7} {v[2]:>8} {v[3]:>10}')
        print('\n--- extensoes SEM texto nenhum (importante: ausência declarada) ---')
        print('  ', ', '.join(sorted(k for k, v in st['res'].items() if not v[3])))


if __name__ == '__main__':
    main()

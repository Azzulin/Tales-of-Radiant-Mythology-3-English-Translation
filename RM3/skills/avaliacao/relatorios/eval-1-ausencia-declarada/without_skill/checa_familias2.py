#!/usr/bin/env python3
"""checa_familias2.py — segunda passada, exaustiva, sobre .zqe .mid .mao .mnm .mso.

Somente leitura da ISO ('rb'). Nada e' escrito na pasta do projeto.

Uso: checa_familias2.py <iso> <lba> <size> <catalogo2.csv> <saida.json> --ferramentas DIR

O que muda em relacao a primeira passada:
  * resolve o arquivo logico pelo `caminho` do catalogo (desce gzip e EZBIND),
    de modo que os 374 `.mnm` que so existem descomprimidos tambem entram;
  * controle POSITIVO de verdade: 40 `.scr` reais resolvidos pelo mesmo caminho;
  * extrai TODA cadeia delimitada por NUL e testa japones com limiar baixo
    (>=2 caracteres kana/kanji), o que maximiza a chance de achar texto;
  * lista cada achado com arquivo, offset, encoding, texto e contexto em hex,
    para julgamento manual — contagem sozinha nao decide nada.
"""
import sys, csv, json, gzip, struct, io, collections

NUL = b'\x00'
SEC = 2048
EXTS = ('zqe', 'mid', 'mao', 'mnm', 'mso')


def sj(b, i):
    if i + 1 >= len(b):
        return 0, None
    c1, c2 = b[i], b[i + 1]
    if not (((0x81 <= c1 <= 0x9F) or (0xE0 <= c1 <= 0xEF)) and
            ((0x40 <= c2 <= 0x7E) or (0x80 <= c2 <= 0xFC))):
        return 0, None
    w = (c1 << 8) | c2
    if 0x829F <= w <= 0x82F1 or 0x8340 <= w <= 0x8396:
        return 2, 'kana'
    if 0x889F <= w <= 0x9FFC or 0xE040 <= w <= 0xEAA4:
        return 2, 'kanji'
    return 0, None


def eu(b, i):
    if i + 1 >= len(b):
        return 0, None
    c1, c2 = b[i], b[i + 1]
    if not (0xA1 <= c1 <= 0xFE and 0xA1 <= c2 <= 0xFE):
        return 0, None
    if c1 in (0xA4, 0xA5):
        return 2, 'kana'
    if 0xB0 <= c1 <= 0xF4:
        return 2, 'kanji'
    return 0, None


def runs(b, fn, minc=2):
    out, i, n = [], 0, len(b)
    while i < n:
        w, _ = fn(b, i)
        if not w:
            i += 1
            continue
        ini, nch, kana = i, 0, False
        while i < n:
            w, cls = fn(b, i)
            if not w:
                break
            nch += 1
            kana = kana or cls == 'kana'
            i += w
        if nch >= minc and kana:
            out.append((ini, b[ini:i], nch))
    return out


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
    """bytes do arquivo logico, seguindo o `caminho` do catalogo."""
    e = porv.get(int(row['entrada_v']))
    if not e:
        return None, 'entrada ausente'
    f.seek(base + e['off'])
    blob = f.read(e['span'])
    partes = row['caminho'].split('/')
    for idx, p in enumerate(partes):
        if blob[:3] == b'\x1f\x8b\x08':
            d = gunz(blob)
            if d is None:
                return None, 'gzip ilegivel'
            blob = d
        if idx == len(partes) - 1:
            break
        t = ezb(blob)
        if not t or partes[idx + 1] not in t:
            return None, 'membro nao achado em ' + p
        do, sz = t[partes[idx + 1]]
        blob = blob[do:do + sz]
    if len(partes) > 1:                       # ultimo componente e' membro
        pass
    tam = int(row['tamanho'])
    if len(blob) > tam and row['off_bdi'] == '':
        pass                                  # gzip inteiro; usa como esta'
    return blob[:tam] if len(blob) >= tam else blob, None


def resolve_direto(f, base, row):
    off, tam = int(row['off_bdi']), int(row['tamanho'])
    f.seek(base + off)
    b = f.read(tam)
    return (b, None) if len(b) == tam else (None, 'leitura curta')


def cadeias_nul(b, minlen=2):
    """Toda cadeia delimitada por NUL (ou pelos limites do arquivo)."""
    out, ini = [], 0
    for i, x in enumerate(b):
        if x == 0:
            if i - ini >= minlen:
                out.append((ini, b[ini:i]))
            ini = i + 1
    if len(b) - ini >= minlen:
        out.append((ini, b[ini:]))
    return out


def hexctx(b, off, n, span=8):
    a = max(0, off - span)
    z = min(len(b), off + n + span)
    return b[a:z].hex()


def main():
    iso, lba, size, cat, saida = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    sys.path.insert(0, sys.argv[sys.argv.index('--ferramentas') + 1])
    from bdi import load_index, validate
    base = lba * SEC
    f = open(iso, 'rb')                       # SOMENTE LEITURA
    buckets, count, entries, sentinel = load_index(f, base)
    bad = validate(buckets, count, entries, sentinel, size)
    if bad:
        print('INDICE REPROVADO', bad)
        sys.exit(2)
    porv = {e['v']: e for e in entries}
    print('indice ok: %d entradas' % count)

    alvo = collections.defaultdict(list)
    scr = []
    with open(cat, newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh):
            nm = row['nome'].lower()
            e = nm.rsplit('.', 1)[-1] if '.' in nm else ''
            if e in EXTS:
                alvo[e].append(row)
            elif e == 'scr' and len(scr) < 40:
                scr.append(row)
    alvo['scr'] = scr

    achados = []
    resumo = {}
    for e in list(EXTS) + ['scr']:
        rows = alvo[e]
        nlido = nerr = 0
        errs = collections.Counter()
        tot_bytes = 0
        n_cad = 0
        cad_jp = 0
        cad_jp_bytes = 0
        run_livre = 0
        arqs_com = set()
        for row in rows:
            if row['off_bdi']:
                b, err = resolve_direto(f, base, row)
            else:
                b, err = resolve(f, base, porv, row)
            if b is None:
                nerr += 1
                errs[err] += 1
                continue
            if b[:3] == b'\x1f\x8b\x08':
                d = gunz(b)
                if d:
                    b = d
            nlido += 1
            tot_bytes += len(b)
            # 1) cadeias NUL-delimitadas com japones -> candidato forte a string de jogo
            for off, c in cadeias_nul(b):
                n_cad += 1
                rs, re_ = runs(c, sj), runs(c, eu)
                if rs or re_:
                    cad_jp += 1
                    cad_jp_bytes += len(c)
                    arqs_com.add(row['caminho'])
                    if len(achados) < 400:
                        achados.append({
                            'ext': e, 'arq': row['caminho'], 'off': off, 'delimitada': True,
                            'tam_cadeia': len(c),
                            'sjis': [(r[1].decode('shift_jis', 'replace'), r[2]) for r in rs[:3]],
                            'euc': [(r[1].decode('euc_jp', 'replace'), r[2]) for r in re_[:3]],
                            'hex': hexctx(b, off, len(c))[:160]})
            # 2) runs soltos (nao delimitados) -> perfil de falso positivo
            for fn, tag in ((sj, 'sjis'), (eu, 'euc')):
                for r in runs(b, fn):
                    ini = r[0]
                    fim = ini + len(r[1])
                    deli = (ini == 0 or b[ini - 1] == 0) and (fim >= len(b) or b[fim] == 0)
                    if not deli:
                        run_livre += 1
                        if len(achados) < 400 and e != 'scr':
                            achados.append({
                                'ext': e, 'arq': row['caminho'], 'off': ini, 'delimitada': False,
                                'tam_cadeia': len(r[1]), tag: [(r[1].decode(
                                    'shift_jis' if tag == 'sjis' else 'euc_jp', 'replace'), r[2])],
                                'hex': hexctx(b, ini, len(r[1]))[:160]})
        resumo[e] = {'arqs_catalogo': len(rows), 'arqs_lidos': nlido, 'arqs_falhou': nerr,
                     'erros': dict(errs), 'bytes_lidos': tot_bytes,
                     'cadeias_nul': n_cad, 'cadeias_nul_com_jp': cad_jp,
                     'bytes_das_cadeias_com_jp': cad_jp_bytes,
                     'runs_jp_nao_delimitados': run_livre,
                     'arqs_com_cadeia_jp': len(arqs_com)}
        print('%-4s cat=%-5d lidos=%-5d falhou=%-4d bytes=%-9d cadeiasNUL=%-7d comJP=%-5d bytesJP=%-7d runsSoltos=%-6d arqsComJP=%d %s' % (
            e, len(rows), nlido, nerr, tot_bytes, n_cad, cad_jp, cad_jp_bytes, run_livre,
            len(arqs_com), dict(errs) if errs else ''))

    print('\n=== cadeias NUL-delimitadas com japones nas 5 familias ===')
    vis = collections.Counter()
    for a in achados:
        if a['ext'] == 'scr' or not a['delimitada']:
            continue
        t = (a.get('sjis') or a.get('euc') or [('', 0)])[0][0]
        vis[(a['ext'], t)] += 1
    for (e, t), n in vis.most_common(40):
        print('  %-4s x%-4d %r' % (e, n, t))
    print('total distintas:', len(vis))

    print('\n=== amostra com contexto (delimitadas) ===')
    m = 0
    for a in achados:
        if a['ext'] == 'scr' or not a['delimitada']:
            continue
        print('  %-4s %-30s off=%-6d tam=%-4d sjis=%s euc=%s hex=%s' % (
            a['ext'], a['arq'], a['off'], a['tam_cadeia'],
            a.get('sjis'), a.get('euc'), a['hex'][:80]))
        m += 1
        if m >= 25:
            break

    print('\n=== amostra de runs NAO delimitados (perfil de falso positivo) ===')
    m = 0
    for a in achados:
        if a['delimitada'] or a['ext'] == 'scr':
            continue
        print('  %-4s %-28s off=%-6d %s %s' % (a['ext'], a['arq'], a['off'],
              a.get('sjis') or a.get('euc'), a['hex'][:60]))
        m += 1
        if m >= 20:
            break

    with open(saida, 'w') as fh:
        json.dump({'resumo': resumo, 'achados': achados}, fh, ensure_ascii=False)
    print('\njson em', saida)
    f.close()


if __name__ == '__main__':
    main()

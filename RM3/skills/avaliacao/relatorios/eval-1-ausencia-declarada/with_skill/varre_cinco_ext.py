#!/usr/bin/env python3
"""Varredura dirigida das cinco familias sem dono: .zqe .mid .mao .mnm .mso

Pergunta: existe texto TRADUZIVEL nessas familias? Se sim, quanto (strings/bytes)?
Se nao, com que confianca se pode riscar do escopo?

Metodo (skill rom-inventario-texto):
  1. valida o indice do namco.bdi antes de qualquer coisa (aborta se reprovar);
  2. desce ate a folha pela MESMA recursao do bdi_catalog2.py (gzip + EZBIND
     aninhado), restrita as entradas que o catalogo diz conter alvo. Cobertura
     conferida contra bdi_catalogo2.csv por extensao; arquivo que nao abre entra
     como 'ilegivel' e NUNCA e' omitido;
  3. discriminador com KANA OBRIGATORIO em trecho maximal de bytes validos,
     testando EUC-JP e Shift-JIS SEPARADAMENTE por arquivo (nunca herdando a
     codificacao de outra frente);
  4. conta em tres baldes: kana (candidato forte), kanji-sem-kana (candidato
     fraco) e ASCII puro (tecnico — nao e' trabalho de traducao);
  5. guarda TODO candidato em CSV para inspecao ocular — contagem de trecho sem
     o texto do trecho nao decide nada.

Limite conhecido (secao 3 da skill): varredura generica acha candidato novo; ela
nao prova que uma frente esta limpa. A conclusao de ausencia aqui se sustenta na
cobertura total da familia + inspecao ocular de 100% dos candidatos, nao no filtro.

Somente leitura. Abre a ISO em 'rb'. Nao escreve nada na pasta do projeto.

Uso: varre_cinco_ext.py <iso> <lba> <size> <catalogo2.csv> <out_prefix>
"""
import sys, os, csv, gzip, zlib, struct, re, json, collections

NUL = b'\x00'
EXTS = ('zqe', 'mid', 'mao', 'mnm', 'mso')
MAXDEPTH = 5

KANA = re.compile(r'[぀-ゟ゠-ヿｦ-ﾝ]')
KANJI = re.compile(r'[㐀-䶿一-鿿]')
ASCII_STR = re.compile(rb'[\x20-\x7e]{4,}')


# ---------------- descida ate a folha (espelha bdi_catalog2.walk) ----------------

def gunzip(blob):
    """Descomprime tolerando lixo/padding depois do fim do membro gzip."""
    try:
        return gzip.decompress(blob)
    except Exception:
        pass
    try:
        return zlib.decompressobj(31).decompress(blob)
    except Exception:
        return None


def ezbind_files(blob):
    if blob[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < count <= 4000) or 0x10 + count * 16 > len(blob):
        return None
    out = []
    for i in range(count):
        no, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(NUL, no) if no < len(blob) else -1
        nome = blob[no:z].decode('latin1') if z > no else ''
        out.append((nome, sz, do))
    return out


def gz_nome(blob):
    if blob[:3] != b'\x1f\x8b\x08' or not (blob[3] & 0x08):
        return None
    z = blob.find(NUL, 10)
    return blob[10:z].decode('latin1') if z > 10 else None


def walk(blob, caminho, depth, leaves, stat):
    """Emite (caminho, conteudo|None) por folha. None = ilegivel."""
    if depth > MAXDEPTH:
        stat['profundidade_estourada'] += 1
        return
    nome_gz = gz_nome(blob)
    if blob[:3] == b'\x1f\x8b\x08':
        d = gunzip(blob)
        if d is None:
            stat['gzip_ilegivel'] += 1
            leaves.append((caminho or nome_gz or '', None))
            return
        blob = d
    fs = ezbind_files(blob)
    if fs is not None:
        stat['ezbind'] += 1
        for nome, sz, do in fs:
            sub = blob[do:do + sz]
            filho = f'{caminho}/{nome}' if caminho else nome
            if sub[:3] == b'\x1f\x8b\x08' or sub[:6] == b'EZBIND':
                walk(sub, filho, depth + 1, leaves, stat)
            else:
                leaves.append((filho, sub))
                stat['folhas'] += 1
        return
    leaves.append((caminho or nome_gz or '', blob))
    stat['folhas'] += 1


# ---------------- discriminador ----------------

def runs(blob, enc):
    """Trechos maximais decodificaveis, >= 6 bytes, separados em tres baldes."""
    kana, kanji, asc = [], [], []
    i, L = 0, len(blob)
    if enc == 'euc_jp':
        lead2 = lambda c: 0xa1 <= c <= 0xfe
        trail = lambda c: 0xa1 <= c <= 0xfe
    else:
        lead2 = lambda c: 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef
        trail = lambda c: 0x40 <= c <= 0xfc and c != 0x7f
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
            except UnicodeDecodeError:
                t = None
            if t is not None:
                (kana if KANA.search(t) else kanji if KANJI.search(t) else asc).append(t)
            i = j
        else:
            i += 1
    return kana, kanji, asc


def scan(blob):
    """Encoding escolhido POR ARQUIVO, pelo peso de bytes em trecho com kana."""
    res, peso = {}, {}
    for enc in ('euc_jp', 'shift_jis'):
        k, kj, a = runs(blob, enc)
        res[enc] = (k, kj, a)
        peso[enc] = sum(len(x.encode(enc)) for x in k)
    melhor = max(peso, key=lambda e: peso[e])
    if peso[melhor] == 0:
        melhor = 'euc_jp'
    k, kj, a = res[melhor]
    return melhor, k, kj, a


# ---------------- principal ----------------

def main():
    iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    cat, pref = sys.argv[4], sys.argv[5]
    sys.path.insert(0, os.path.dirname(os.path.abspath(cat)) + '/../ferramentas')
    from bdi import load_index, validate, SEC
    base = lba * SEC

    esperado = collections.Counter()
    alvo_v = set()
    with open(cat, newline='', encoding='utf-8') as c:
        for r in csv.DictReader(c):
            n = r['nome']
            e = n.rsplit('.', 1)[-1].lower() if '.' in n else ''
            if e in EXTS:
                esperado[e] += 1
                alvo_v.add(int(r['entrada_v']))
    print('catalogo espera:', dict(esperado), 'total', sum(esperado.values()),
          'em', len(alvo_v), 'entradas do bdi')

    agg = {e: {'n': 0, 'bytes': 0, 'ilegivel': 0, 'arq_kana': 0, 'arq_kanji': 0,
               'kana_runs': 0, 'kana_bytes': 0, 'kanji_runs': 0, 'kanji_bytes': 0,
               'ascii_runs': 0, 'enc': collections.Counter()} for e in EXTS}
    cand, cabec = [], collections.defaultdict(collections.Counter)
    ascii_am = collections.defaultdict(collections.Counter)
    stat = {'ezbind': 0, 'folhas': 0, 'gzip_ilegivel': 0, 'profundidade_estourada': 0}

    with open(iso, 'rb') as f:                      # SOMENTE LEITURA
        buckets, count, entries, sentinel = load_index(f, base)
        bad = validate(buckets, count, entries, sentinel, size)
        if bad:
            print('INDICE REPROVADO — abortando:')
            for b in bad:
                print('  ', b)
            sys.exit(2)
        print(f'indice OK: {count} entradas, sentinela == {size}')

        for e in entries:
            if e['v'] not in alvo_v:
                continue
            f.seek(base + e['off'])
            leaves = []
            walk(f.read(e['span']), '', 0, leaves, stat)
            for caminho, blob in leaves:
                nome = caminho.split('/')[-1]
                ext = nome.rsplit('.', 1)[-1].lower() if '.' in nome else ''
                if ext not in EXTS:
                    continue
                a = agg[ext]
                a['n'] += 1
                if blob is None:
                    a['ilegivel'] += 1
                    continue
                a['bytes'] += len(blob)
                cabec[ext][blob[:8].hex()] += 1
                for m in ASCII_STR.findall(blob[:4096]):
                    ascii_am[ext][m.decode('latin1')] += 1
                enc, kana, kanji, asc = scan(blob)
                a['enc'][enc if kana else '-'] += 1
                a['ascii_runs'] += len(asc)
                if kana:
                    a['arq_kana'] += 1
                    a['kana_runs'] += len(kana)
                    a['kana_bytes'] += sum(len(x.encode(enc)) for x in kana)
                    cand += [(ext, caminho, 'kana', enc, t) for t in kana]
                if kanji:
                    a['arq_kanji'] += 1
                    a['kanji_runs'] += len(kanji)
                    a['kanji_bytes'] += sum(len(x.encode(enc)) for x in kanji)
                    cand += [(ext, caminho, 'kanji', enc, t) for t in kanji]

    print('\n--- COBERTURA (lido vs catalogo recursivo) ---')
    ok = True
    for e in EXTS:
        got, exp = agg[e]['n'], esperado[e]
        print(f'  {e:<4} lidos={got:<5} catalogo={exp:<5} ilegivel={agg[e]["ilegivel"]:<4}'
              f' {"OK" if got == exp else "DIVERGE"}')
        ok &= got == exp
    print('cobertura', 'COMPLETA' if ok else 'INCOMPLETA',
          '| profundidade_estourada=%d gzip_ilegivel=%d ezbind_abertos=%d'
          % (stat['profundidade_estourada'], stat['gzip_ilegivel'], stat['ezbind']))

    print('\n--- POR EXTENSAO (kana obrigatorio) ---')
    for e in EXTS:
        a = agg[e]
        print(f'  {e:<4} n={a["n"]:<5} bytes={a["bytes"]:<9} '
              f'arq_kana={a["arq_kana"]:<4} tr_kana={a["kana_runs"]:<5} '
              f'b_kana={a["kana_bytes"]:<7} arq_kanji={a["arq_kanji"]:<4} '
              f'tr_kanji={a["kanji_runs"]:<5} b_kanji={a["kanji_bytes"]:<7} '
              f'tr_ascii={a["ascii_runs"]:<6} enc={dict(a["enc"])}')

    with open(pref + '_candidatos.csv', 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['ext', 'arquivo', 'classe', 'encoding', 'texto', 'bytes'])
        for ext, arq, cl, enc, t in cand:
            w.writerow([ext, arq, cl, enc, t, len(t.encode(enc))])

    print('\n--- CANDIDATOS DISTINTOS (para inspecao ocular) ---')
    for e in EXTS:
        for cl in ('kana', 'kanji'):
            d = collections.Counter(t for x, _, c2, _, t in cand if x == e and c2 == cl)
            if not d:
                continue
            print(f'  [{e}/{cl}] {sum(d.values())} ocorrencias, {len(d)} distintas; top:')
            for t, n in d.most_common(12):
                print(f'      {n:>5}x  {t!r}')

    with open(pref + '_forma.json', 'w', encoding='utf-8') as o:
        json.dump({'cabecalhos': {e: dict(cabec[e].most_common(6)) for e in EXTS},
                   'ascii': {e: dict(ascii_am[e].most_common(20)) for e in EXTS},
                   'agg': {e: {k: (dict(v) if isinstance(v, collections.Counter) else v)
                               for k, v in agg[e].items()} for e in EXTS}},
                  o, ensure_ascii=False, indent=1)
    print(f'\n{len(cand)} candidatos em {pref}_candidatos.csv; forma em {pref}_forma.json')


if __name__ == '__main__':
    main()

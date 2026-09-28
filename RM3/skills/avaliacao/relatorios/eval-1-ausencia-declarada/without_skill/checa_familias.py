#!/usr/bin/env python3
"""checa_familias.py — ha texto traduzivel em .zqe .mid .mao .mnm .mso do namco.bdi?

Somente leitura. Abre a ISO em 'rb'. Nao escreve nada dentro da pasta do projeto.

Uso:
  checa_familias.py <iso> <lba> <size> <bdi_catalogo2.csv> <saida.json> [--ferramentas DIR]

Metodo (tres provas independentes por familia):
  1) IDENTIDADE DO FORMATO   — magic / cabecalho, entropia, %zero, %ASCII imprimivel;
     e o teste de "banco de texto": u32/u16 count + tabela de offsets crescente
     dentro do arquivo (a assinatura que TXZ/OLDATA/PTRTAB/FaceChat tem).
  2) DISCRIMINADOR DE JAPONES CALIBRADO — runs maximos de kana/kanji em Shift-JIS
     e EUC-JP, exigindo >=1 kana no run. Rodado tambem em controles positivos
     (.scr, texto real) e negativos (.ppt, textura) para medir a taxa base.
  3) DELIMITACAO — string de jogo neste jogo e NUL-terminada e apontada por tabela.
     Mede-se a fracao de runs que comeca/termina em NUL e a repeticao dos runs
     (texto real repete; ruido de float nao).
"""
import sys, os, csv, json, gzip, math, struct, io, collections

NUL = b'\x00'
SEC = 2048
EXTS = ('zqe', 'mid', 'mao', 'mnm', 'mso')
CONTROLES = {'scr': 'controle_positivo', 'ppt': 'controle_negativo'}
N_CONTROLE = 40


# ---------------------------------------------------------------- japones
def _sjis_char(b, i):
    """Devolve (nchars_bytes, classe) para Shift-JIS DBCS em b[i]. classe: kana|kanji|None"""
    if i + 1 >= len(b):
        return 0, None
    c1, c2 = b[i], b[i + 1]
    lead = (0x81 <= c1 <= 0x9F) or (0xE0 <= c1 <= 0xEF)
    trail = (0x40 <= c2 <= 0x7E) or (0x80 <= c2 <= 0xFC)
    if not (lead and trail):
        return 0, None
    w = (c1 << 8) | c2
    if 0x829F <= w <= 0x82F1:
        return 2, 'kana'          # hiragana
    if 0x8340 <= w <= 0x8396:
        return 2, 'kana'          # katakana
    if 0x889F <= w <= 0x9FFC or 0xE040 <= w <= 0xEAA4:
        return 2, 'kanji'
    return 0, None


def _euc_char(b, i):
    if i + 1 >= len(b):
        return 0, None
    c1, c2 = b[i], b[i + 1]
    if not (0xA1 <= c1 <= 0xFE and 0xA1 <= c2 <= 0xFE):
        return 0, None
    if c1 == 0xA4:
        return 2, 'kana'
    if c1 == 0xA5:
        return 2, 'kana'
    if 0xB0 <= c1 <= 0xF4:
        return 2, 'kanji'
    return 0, None


def runs_jp(b, charfn, min_chars=3):
    """Runs maximos de kana/kanji com >=1 kana e >=min_chars caracteres.
    Devolve lista de (inicio, bytes_do_run, nchars, tem_nul_antes, tem_nul_depois)."""
    out = []
    i = 0
    n = len(b)
    while i < n:
        w, cls = charfn(b, i)
        if not w:
            i += 1
            continue
        ini = i
        nch = 0
        temkana = False
        while i < n:
            w, cls = charfn(b, i)
            if not w:
                break
            nch += 1
            if cls == 'kana':
                temkana = True
            i += w
        if nch >= min_chars and temkana:
            antes = (ini == 0) or (b[ini - 1] == 0)
            depois = (i >= n) or (b[i] == 0)
            out.append((ini, b[ini:i], nch, antes, depois))
    return out


# ---------------------------------------------------------------- perfil
def entropia(b):
    if not b:
        return 0.0
    h = collections.Counter(b)
    n = len(b)
    return -sum((c / n) * math.log2(c / n) for c in h.values())


def ascii_strings(b, minlen=4):
    out, cur = [], bytearray()
    for x in b:
        if 0x20 <= x < 0x7F:
            cur.append(x)
        else:
            if len(cur) >= minlen:
                out.append(bytes(cur).decode('ascii'))
            cur = bytearray()
    if len(cur) >= minlen:
        out.append(bytes(cur).decode('ascii'))
    return out


def tabela_de_texto(b):
    """A assinatura de banco de texto deste jogo: contador + tabela de offsets
    estritamente crescente, o primeiro offset caindo no fim da tabela, e o
    ultimo dentro do arquivo. Testa u32 e u16, com cabecalho de 4 ou 2 bytes.
    Devolve descricao se casar, senao None."""
    n = len(b)
    for larg, unp in ((4, '<I'), (2, '<H')):
        if n < larg * 3:
            continue
        cnt = struct.unpack_from(unp, b, 0)[0]
        if not (2 <= cnt <= 4000):
            continue
        fim = larg + cnt * larg
        if fim > n:
            continue
        offs = list(struct.unpack_from('<%d%s' % (cnt, unp[1]), b, larg))
        if any(offs[i] >= offs[i + 1] for i in range(cnt - 1)):
            continue
        if offs[-1] >= n:
            continue
        # o primeiro offset tem de apontar para logo depois da tabela
        # (aceita base relativa 0 ou base absoluta)
        if offs[0] in (0, fim) or abs(offs[0] - fim) <= larg:
            return 'count u%d + %d offsets crescentes, off[0]=%d, fim_tab=%d' % (
                larg * 8, cnt, offs[0], fim)
    return None


def perfila(nome, b):
    z = b.count(0)
    pr = sum(1 for x in b if 0x20 <= x < 0x7F)
    rs = runs_jp(b, _sjis_char)
    re_ = runs_jp(b, _euc_char)
    st = ascii_strings(b)
    return {
        'nome': nome, 'tam': len(b),
        'head8': b[:8].hex(), 'head_ascii': ''.join(chr(x) if 32 <= x < 127 else '.' for x in b[:8]),
        'entropia': round(entropia(b), 3),
        'pct_zero': round(100.0 * z / len(b), 1) if b else 0,
        'pct_ascii': round(100.0 * pr / len(b), 1) if b else 0,
        'tab_texto': tabela_de_texto(b),
        'sjis_runs': len(rs), 'sjis_bytes': sum(len(r[1]) for r in rs),
        'sjis_delim': sum(1 for r in rs if r[3] and r[4]),
        'euc_runs': len(re_), 'euc_bytes': sum(len(r[1]) for r in re_),
        'euc_delim': sum(1 for r in re_ if r[3] and r[4]),
        'ascii_n': len(st), 'ascii_ex': st[:6],
        'sjis_ex': [(r[1].decode('shift_jis', 'replace'), r[2], r[3], r[4]) for r in rs[:4]],
        'euc_ex': [(r[1].decode('euc_jp', 'replace'), r[2], r[3], r[4]) for r in re_[:4]],
    }


# ---------------------------------------------------------------- leitura
def main():
    iso, lba, size, cat, saida = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    if '--ferramentas' in sys.argv:
        sys.path.insert(0, sys.argv[sys.argv.index('--ferramentas') + 1])
    from bdi import load_index, validate

    base = lba * SEC
    f = open(iso, 'rb')                       # SOMENTE LEITURA
    buckets, count, entries, sentinel = load_index(f, base)
    falhas = validate(buckets, count, entries, sentinel, size)
    if falhas:
        print('INDICE REPROVADO:', falhas)
        sys.exit(2)
    porv = {e['v']: e for e in entries}
    print('indice ok: %d entradas, sentinela %d' % (count, sentinel))

    # seleciona linhas do catalogo
    alvo = collections.defaultdict(list)
    ctrl = collections.defaultdict(list)
    with open(cat, newline='', encoding='utf-8', errors='replace') as fh:
        for row in csv.DictReader(fh):
            nm = row['nome'].lower()
            e = nm.rsplit('.', 1)[-1] if '.' in nm else ''
            if e in EXTS:
                alvo[e].append(row)
            elif e in CONTROLES and len(ctrl[e]) < N_CONTROLE and row['off_bdi']:
                ctrl[e].append(row)

    def le(row):
        """bytes do arquivo logico. Nunca escreve. Devolve None se inacessivel."""
        if row['off_bdi']:
            off = int(row['off_bdi'])
            tam = int(row['tamanho'])
            f.seek(base + off)
            b = f.read(tam)
            if len(b) != tam:
                return None
            if b[:3] == b'\x1f\x8b\x08':        # .scr e afins vem gzipados
                try:
                    return gzip.decompress(b)
                except Exception:
                    return b
            return b
        # conteudo que so existe descomprimido: le a entrada e descomprime
        e = porv.get(int(row['entrada_v']))
        if not e:
            return None
        f.seek(base + e['off'])
        raw = f.read(e['span'])
        if raw[:3] != b'\x1f\x8b\x08':
            return None
        try:
            return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        except Exception:
            return None

    res = {}
    for grupo, fonte in (('familia', alvo), ('controle', ctrl)):
        for e, rows in sorted(fonte.items()):
            perfis, falhou = [], 0
            for row in rows:
                b = le(row)
                if b is None:
                    falhou += 1
                    continue
                perfis.append(perfila(row['caminho'], b))
            res[e] = {'grupo': grupo, 'rotulo': CONTROLES.get(e, 'a_investigar'),
                      'n_catalogo': len(rows), 'n_lido': len(perfis), 'n_falhou': falhou,
                      'perfis': perfis}
            print('%-4s %-18s lidos %4d/%4d' % (e, res[e]['rotulo'], len(perfis), len(rows)))

    # ---- agregados
    print('\n%-5s %-18s %6s %10s %7s %6s %6s %8s %6s %8s %6s %6s' % (
        'ext', 'rotulo', 'arqs', 'bytes', 'entrop', '%zero', 'tabTx',
        'sjisRun', 'delim', 'eucRun', 'delim', 'jpB'))
    resumo = {}
    for e, d in res.items():
        p = d['perfis']
        if not p:
            continue
        tb = sum(1 for x in p if x['tab_texto'])
        sr = sum(x['sjis_runs'] for x in p); sd = sum(x['sjis_delim'] for x in p)
        er = sum(x['euc_runs'] for x in p); ed = sum(x['euc_delim'] for x in p)
        jb = sum(x['sjis_bytes'] for x in p) + sum(x['euc_bytes'] for x in p)
        tot = sum(x['tam'] for x in p)
        ent = sum(x['entropia'] for x in p) / len(p)
        zer = sum(x['pct_zero'] for x in p) / len(p)
        resumo[e] = {'rotulo': d['rotulo'], 'arqs': len(p), 'bytes': tot,
                     'entropia_media': round(ent, 2), 'pct_zero_medio': round(zer, 1),
                     'arqs_com_tabela_de_texto': tb,
                     'sjis_runs': sr, 'sjis_runs_delimitados': sd,
                     'euc_runs': er, 'euc_runs_delimitados': ed, 'bytes_jp_candidatos': jb,
                     'arqs_com_algum_run': sum(1 for x in p if x['sjis_runs'] or x['euc_runs']),
                     'ascii_total': sum(x['ascii_n'] for x in p),
                     'heads': collections.Counter(x['head8'][:8] for x in p).most_common(4)}
        print('%-5s %-18s %6d %10d %7.2f %6.1f %6d %8d %6d %8d %6d %8d' % (
            e, d['rotulo'], len(p), tot, ent, zer, tb, sr, sd, er, ed, jb))

    # ---- repeticao dos runs (texto real repete; ruido nao)
    print('\n--- runs mais frequentes por extensao (texto real repete) ---')
    for e, d in res.items():
        c = collections.Counter()
        for x in d['perfis']:
            for s in x['sjis_ex']:
                c[('sjis', s[0])] += 1
            for s in x['euc_ex']:
                c[('euc', s[0])] += 1
        top = c.most_common(6)
        resumo[e]['runs_top'] = [[k[0], k[1], v] for k, v in top]
        print(e, '->', top if top else 'nenhum run')

    print('\n--- amostra de ASCII por extensao ---')
    for e, d in res.items():
        ex = []
        for x in d['perfis']:
            ex.extend(x['ascii_ex'])
            if len(ex) > 12:
                break
        resumo[e]['ascii_amostra'] = ex[:12]
        print(e, '->', ex[:12])

    print('\n--- head de um arquivo por extensao ---')
    for e, d in res.items():
        if d['perfis']:
            x = d['perfis'][0]
            print('%-5s %-28s tam=%-7d %s  %s  tab=%s' % (
                e, x['nome'], x['tam'], x['head8'], x['head_ascii'], x['tab_texto']))

    with open(saida, 'w') as fh:
        json.dump({'resumo': resumo, 'detalhe': res}, fh, ensure_ascii=False)
    print('\njson em', saida)
    f.close()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Build multi-bloco do EBOOT: reempacota cada arena e reescreve os ponteiros.

Uso: eboot_build2.py <limpo> <saida.bin> <lote1.csv> [lote2.csv ...] [--aplicar]

DRY-RUN por padrao. Escreve SEMPRE em arquivo novo, nunca no LIMPO.
Cada `bloco` do CSV tem sua propria arena, medida das linhas daquele bloco.

Guardas, antes de qualquer escrita:
  1. cada ponteiro do lote aponta hoje para a string que o lote declara
  2. nenhum ponteiro de FORA do lote aponta para dentro de qualquer arena
  3. arenas de blocos diferentes nao se sobrepoem
  4. o pool novo de cada bloco cabe na sua arena
  5. o tamanho do arquivo nao muda

`traducao` == '(verbatim)' -> mantem os bytes originais. Bytes iguais no mesmo
bloco sao deduplicados: uma string no pool, varios ponteiros (P-42.3).

Ver P-42.4 (metodo), P-43 (bloco da criacao), P-44 (primeiro build).
"""
import sys, csv, re, struct, hashlib, collections

ELF_FIM = 5862704
DELTA = 0x08803000
PAD = b'\x00'


def main():
    limpo, saida = sys.argv[1], sys.argv[2]
    lotes = [a for a in sys.argv[3:] if not a.startswith('--')]
    aplicar = '--aplicar' in sys.argv

    raw = bytearray(open(limpo, 'rb').read())
    n0 = len(raw)
    assert raw[:4] == b'\x7fELF', 'LIMPO nao e ELF'
    print(f'LIMPO {n0} B  sha256={hashlib.sha256(raw).hexdigest()[:16]}')

    rows = []
    for L in lotes:
        rs = list(csv.DictReader(open(L, encoding='utf-8')))
        for r in rs:
            r.setdefault('bloco', 'criacao')
            if not r.get('bloco'):
                r['bloco'] = 'criacao'
        rows += rs
        print(f'  {L}: {len(rs)} linhas')
    blocos = collections.OrderedDict()
    for r in rows:
        blocos.setdefault(r['bloco'], []).append(r)

    # --- guarda 1: ponteiros conferem ---
    for nome, rs in blocos.items():
        for r in rs:
            vp, vs = int(r['va_ponteiro'], 16), int(r['va_string'], 16)
            w, = struct.unpack_from('<I', raw, vp - DELTA)
            if w != vs:
                print(f'RECUSADO: 0x{vp:08X} aponta 0x{w:08X}, lote diz 0x{vs:08X}')
                return 1
    print(f'guarda 1 — {len(rows)} ponteiros conferem com os lotes  OK')

    # --- arenas ---
    arenas = {}
    for nome, rs in blocos.items():
        # Arena EXPLICITA (colunas arena_ini/arena_fim) quando o lote a declara:
        # um bloco cujo texto e' picado por tabelas de ponteiro precisa dizer
        # onde cada pedaco comeca e acaba, porque min..max das strings
        # atravessaria as tabelas (P-67.12). Sem essas colunas, o padrao de
        # sempre: a arena e' o tanto que as proprias strings ocupam.
        if rs[0].get('arena_ini') and rs[0].get('arena_fim'):
            a_ini = int(rs[0]['arena_ini'], 16)
            a_fim = int(rs[0]['arena_fim'], 16)
        else:
            vs = [(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs]
            a_ini = min(v for v, _ in vs)
            a_fim = max(v + b + 1 for v, b in vs)
        arenas[nome] = (a_ini, a_fim)
        print(f'  [{nome}] arena 0x{a_ini:08X}..0x{a_fim:08X} = {a_fim-a_ini} B, '
              f'{len(rs)} ponteiros')

    # --- guarda 3: arenas nao se sobrepoem ---
    ords = sorted(arenas.items(), key=lambda kv: kv[1][0])
    for (n1, (i1, f1)), (n2, (i2, f2)) in zip(ords, ords[1:]):
        if f1 > i2:
            print(f'RECUSADO: arenas {n1} e {n2} se sobrepoem')
            return 1
    print('guarda 3 — arenas disjuntas  OK')

    # --- guarda 2: nenhum ponteiro externo aponta para dentro de arena ---
    do_lote = {int(r['va_string'], 16) for r in rows}
    intrusos = []
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        for nome, (a, f) in arenas.items():
            if a <= w < f and w not in do_lote:
                intrusos.append((q + DELTA, w, nome))
    if intrusos:
        print(f'RECUSADO: {len(intrusos)} ponteiros de fora apontam para dentro de arena')
        for vp, w, nm in intrusos[:10]:
            print(f'  0x{vp:08X} -> 0x{w:08X} (arena {nm})')
        return 1
    print('guarda 2 — 0 ponteiros externos apontam para dentro das arenas  OK')

    # --- guarda 2b: nenhum PONTEIRO MORA dentro de uma arena (P-67.12) ---
    # A guarda 2 olha o ALVO dos ponteiros de fora; esta olha o ENDERECO deles.
    # Em `valuables`/`foot_equip`/`enhance_material` a tabela de registros fica
    # NO MEIO do texto, entao reempacotar a arena escreve o pool por cima dos
    # proprios ponteiros e destroi a tabela. Guarda 2 nao pegava: sao ponteiros
    # DO lote, nao de fora. Custou uma ISO (en12, descartada).
    dentro = collections.Counter()
    for r in rows:
        vp = int(r['va_ponteiro'], 16)
        for nome, (a, f) in arenas.items():
            if a <= vp < f:
                dentro[(r['bloco'], nome)] += 1
    if dentro:
        print(f'RECUSADO: ponteiros moram dentro de arena — o pool os sobrescreveria')
        for (src, nm), c in dentro.most_common(10):
            print(f'  {c} ponteiros do bloco {src} dentro da arena {nm}')
        return 1
    print('guarda 2b — nenhum ponteiro mora dentro de arena  OK')

    # --- guarda 2c: nenhum NOME DE ARQUIVO dentro de arena (P-77) ---
    # Reempacotar uma arena MOVE tudo que esta nela. Para texto isso e' inocuo
    # (o ponteiro e' reescrito junto), mas os blocos-regiao do P-68 nao sao so'
    # texto: `questfiltro` contem `cl001.ppt`..`cl027.ppt`, que sao arquivos DE
    # VERDADE dentro do `namco.bdi` (o modelo de cada classe, carregado logo
    # depois da criacao de personagem), e `bgm` contem `bgm017.at3`.. — 130
    # nomes ao todo, arrastados para o pool como `(verbatim)` pelo
    # `lote_extras_gera.py` so' para calar a guarda 2.
    #
    # Nome de arquivo nao se traduz e nao se muda de lugar. A arena tem de ser
    # picada de modo que ele fique de FORA — e' o que `segmentos_livres` faz
    # quando o dado alheio esta no meio das strings do lote. Esta guarda existe
    # para que "esqueci de re-segmentar" nunca mais chegue a uma ISO.
    NOME_ARQ = re.compile(rb'^[A-Za-z0-9_\-]{1,40}\.[A-Za-z0-9]{2,4}$')
    arquivos = []
    for nome, (a, f) in arenas.items():
        q = a
        while q < f:
            z = raw.find(b'\x00', q - DELTA, f - DELTA)
            if z < 0:
                break
            s = bytes(raw[q - DELTA:z])
            if s and NOME_ARQ.match(s):
                arquivos.append((nome, q, s.decode('ascii')))
            q = z + 1 + DELTA
            while q < f and raw[q - DELTA] == 0:
                q += 1
    if arquivos:
        print(f'RECUSADO: {len(arquivos)} nomes de arquivo dentro de arena — '
              f'o pool os moveria de lugar e o jogo nao acharia o recurso')
        for nm, va, s in arquivos[:10]:
            print(f'  [{nm}] 0x{va:08X} {s}')
        return 1
    print('guarda 2c — nenhum nome de arquivo dentro de arena  OK')

    # --- monta os pools ---
    destino = {}
    pools = {}
    for nome, rs in blocos.items():
        a_ini, a_fim = arenas[nome]
        pool = bytearray()
        onde = {}
        for r in rs:
            if r['traducao'] == '(verbatim)':
                p = int(r['va_string'], 16) - DELTA
                novo = bytes(raw[p:p + int(r['bytes_jp'])])
            else:
                novo = r['traducao'].replace('\\n', '\n').encode('ascii')
            if novo in onde:
                destino[int(r['va_ponteiro'], 16)] = onde[novo]
                continue
            onde[novo] = a_ini + len(pool)
            destino[int(r['va_ponteiro'], 16)] = onde[novo]
            pool += novo + b'\x00'
        tam = a_fim - a_ini
        if len(pool) > tam:
            print(f'RECUSADO: [{nome}] pool {len(pool)} B nao cabe em {tam} B')
            return 1
        print(f'  [{nome}] pool {len(pool)} B em {tam} B, {len(onde)} distintas, '
              f'folga {tam-len(pool):+d}')
        pools[nome] = pool + PAD * (tam - len(pool))
    print('guarda 4 — todos os pools cabem  OK')

    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    out = bytearray(raw)
    for nome, pool in pools.items():
        a_ini, a_fim = arenas[nome]
        out[a_ini - DELTA:a_fim - DELTA] = pool
    for vp, vs in destino.items():
        struct.pack_into('<I', out, vp - DELTA, vs)
    if len(out) != n0:
        print(f'RECUSADO: tamanho mudou {len(out)} != {n0}')
        return 1
    print('guarda 5 — tamanho inalterado  OK')

    open(saida, 'wb').write(out)
    print(f'\n-> {saida}  {len(out)} B  sha256={hashlib.sha256(out).hexdigest()[:16]}')

    dif = [i for i in range(n0) if raw[i] != out[i]]
    faixas = []
    for i in dif:
        if faixas and i == faixas[-1][1] + 1:
            faixas[-1][1] = i
        else:
            faixas.append([i, i])
    print(f'DIFF: {len(dif)} bytes em {len(faixas)} faixas')
    por = collections.Counter()
    for a, b in faixas:
        va = a + DELTA
        alvo = next((n for n, (i, f) in arenas.items() if i <= va < f), None)
        if alvo:
            por[f'arena {alvo}'] += b - a + 1
        elif any(vp - DELTA <= a and b < vp - DELTA + 4 for vp in destino):
            por['tabela de ponteiros'] += b - a + 1
        else:
            por['FORA'] += b - a + 1
    for k, v in por.items():
        print(f'  {k}: {v} bytes')
    return 1 if por['FORA'] else 0


if __name__ == '__main__':
    sys.exit(main())

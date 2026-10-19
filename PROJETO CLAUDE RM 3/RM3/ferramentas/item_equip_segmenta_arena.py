#!/usr/bin/env python3
"""Quebra cada bloco em quantas sub-arenas forem precisas para que NENHUMA
delas contenha um ponteiro, e reparte o texto entre elas por capacidade
(P-67.12).

Por que: em `valuables`, `foot_equip` e `enhance_material` a tabela de
registros nao fica antes nem depois do texto — fica NO MEIO dele. Como
`eboot_build2.py` deriva a arena de min(va_string) a max(va_string+bytes), a
arena desses blocos engole a propria tabela, e reempacotar o pool escreve texto
por cima dos ponteiros. Passava as guardas 1-4 e saia corrompido — custou a ISO
`en12`, descartada; ver a guarda 2b, acrescentada ao `eboot_build2.py` para que
isso nao possa mais passar.

Duas coisas, entao:

1. Corta o bloco nos segmentos maximais livres de ponteiro, cada um virando
   `<bloco>__sN`, e declara a arena de cada um em `arena_ini`/`arena_fim` (o
   segmento INTEIRO, nao so' o pedaco que as strings de hoje ocupam).

2. Reparte as strings entre esses segmentos por capacidade, e nao pela posicao
   em que nasceram. Isso importa: em `valuables` o segmento do meio nasce com
   73.904 B de texto para 47.509 B de espaco, enquanto os outros dois sobram —
   deixar cada string onde estava exigiria cortar 36% do texto, e repartindo
   nao falta nada. Pode fazer isso porque `eboot_build2.py` reescreve TODO
   ponteiro do lote: uma string cabe em qualquer segmento do mesmo bloco-pai.

Strings identicas viajam juntas, para continuarem deduplicadas no pool.

Uso:
  item_equip_segmenta_arena.py <csv...> --ponteiros <csv...> [--aplicar]

`--ponteiros` lista TODOS os lotes do build, porque um ponteiro de qualquer
frente que more dentro da arena e' igualmente fatal.
"""
import sys, os, csv, argparse, collections, re

NUL = b'\x00'


def le(p):
    with open(p, encoding='utf-8') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def segmentos_livres(ini, fim, ptrs, strs, raw=None, delta=0x08803000):
    """Faixas de [ini,fim) livres de ponteiro E que realmente guardam texto.

    Nao basta tirar os ponteiros: entre um ponteiro e o proximo ficam os CAMPOS
    do registro (`valor`, `id_categoria`, flags — P-67.9), e escrever texto ali
    destroi o item. No banco de `valuables` sao 1.012 buracos de 12 B, todos
    campo de dado vivo: nenhum contem string do lote, nenhum e' zerado. Usa-los
    como pool corromperia preco e categoria de 1.012 itens (P-67.14).

    O criterio seguro: so' vale a faixa onde as strings do lote JA' moram, e so'
    ate' onde elas moram. O que houver antes da primeira ou depois da ultima
    string do segmento e' de outra pessoa, e fica de fora.
    """
    proib = sorted((p, p + 4) for p in ptrs if ini <= p < fim)
    brutos, cur = [], ini
    for a, b in proib:
        if a > cur:
            brutos.append((cur, a))
        cur = max(cur, b)
    if cur < fim:
        brutos.append((cur, fim))

    livres = []
    for a, b in brutos:
        dentro = sorted((v, n) for v, n in strs if a <= v and v + n + 1 <= b)
        if not dentro:
            continue                       # buraco sem texto: campo de registro
        if raw is None:
            livres.append((min(v for v, _ in dentro),
                           max(v + n + 1 for v, n in dentro)))
            continue
        # Quebra tambem onde ha DADO que nao pertence ao lote. Entre duas
        # strings do lote pode morar texto que ninguem aponta (P-70), ponteiro,
        # ou binario — e o pool passaria por cima. Cobrir so' os ponteiros nao
        # basta: foi o que quebrou o `ui` e o `questfiltro` no `en12` (P-77).
        cur_i = dentro[0][0]
        cur_f = dentro[0][0] + dentro[0][1] + 1
        for v, n in dentro[1:]:
            vazio = raw[cur_f - delta:v - delta]
            if vazio.strip(NUL):      # ha dado no meio: fecha o segmento
                livres.append((cur_i, cur_f))
                cur_i = v
            cur_f = v + n + 1
        livres.append((cur_i, cur_f))
    return livres


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--ponteiros', nargs='+', required=True)
    ap.add_argument('--eboot', default='eboot/EBOOT_dec_LIMPO.bin',
                    help='necessario para ver DADO nao coberto entre as strings; '
                         'sem ele a arena engole o que nao e do lote (P-77)')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    raw = None
    if args.eboot and os.path.exists(args.eboot):
        raw = open(args.eboot, 'rb').read()
        print(f'conferindo dado nao coberto contra {args.eboot}')
    else:
        print('AVISO: sem EBOOT, a arena so evita ponteiro — dado entre strings '
              'nao sera detectado')

    ptrs = set()
    for p in args.ponteiros:
        for r in le(p)[1]:
            ptrs.add(int(r['va_ponteiro'], 16))
    print(f'{len(ptrs)} ponteiros distintos considerados\n')

    arqs = {p: le(p) for p in args.csvs}
    todas = [r for p in args.csvs for r in arqs[p][1]]

    pai = collections.OrderedDict()
    for r in todas:
        pai.setdefault(re.sub(r'__s\d+$', '', r['bloco']), []).append(r)

    tot_seg = falhou = 0
    for nome, rs in pai.items():
        vs = {(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs}
        ini, fim = min(v for v, _ in vs), max(v + n + 1 for v, n in vs)
        livres = segmentos_livres(ini, fim, ptrs, vs, raw)
        if len(livres) <= 1:
            for r in rs:                                  # ja' era contiguo
                r['bloco'] = nome
                r['arena_ini'] = r['arena_fim'] = ''
            continue

        # unidades = strings distintas (identicas viajam juntas, p/ dedup).
        # `(verbatim)` NAO e' texto: o build copia os `bytes_jp` originais, e
        # cada string tem os seus — duas verbatim nao deduplicam entre si, e
        # custam o tamanho do japones, nao os 11 caracteres da palavra.
        grupos = collections.OrderedDict()
        for r in rs:
            chave = (('V', r['va_string']) if r['traducao'] == '(verbatim)'
                     else r['traducao'])
            grupos.setdefault(chave, []).append(r)

        def custo(chave, linhas):
            if isinstance(chave, tuple):
                return int(linhas[0]['bytes_jp']) + 1
            return len(chave.replace('\\n', '\n').encode('ascii', 'replace')) + 1

        cap = [(a, b, b - a) for a, b in livres]

        def casa(va):
            """segmento que contem o lugar ORIGINAL da string."""
            for k, (a, b, _) in enumerate(cap):
                if a <= va < b:
                    return k
            return None

        # --- fase 1: linha de base, tudo `(verbatim)` onde ja' mora ---
        # Isto sempre cabe, por construcao: o custo de uma string em japones e'
        # exatamente o espaco que ela ja' ocupa dentro do proprio segmento.
        # Comecar por aqui e' o que garante que NENHUMA linha precise ser
        # descartada — e descartar era um laco de realimentacao: a linha
        # descartada virava dado alheio, o dado alheio partia o segmento, o
        # segmento menor descartava mais linhas (P-77).
        usado = [0] * len(cap)
        lar = {}                       # va_string -> segmento
        flut = []                      # string que nao cai em segmento nenhum
        for r in rs:
            va = int(r['va_string'], 16)
            if va in lar:
                continue
            k = casa(va)
            if k is None:
                flut.append(va)
                continue
            lar[va] = k
            usado[k] += int(r['bytes_jp']) + 1

        # --- fase 2: promover a traducao o que couber, melhor ganho primeiro ---
        # Promover um grupo devolve aos segmentos de origem o japones de cada
        # string dele e gasta o ingles UMA vez (dedup) no segmento escolhido.
        prom = set()
        cands = []
        for chave, linhas in grupos.items():
            if isinstance(chave, tuple):          # ja' e' `(verbatim)`
                continue
            tam = {}
            for r in linhas:
                tam[int(r['va_string'], 16)] = int(r['bytes_jp']) + 1
            if any(v not in lar for v in tam):    # tem string fora de segmento
                continue
            libera = sum(tam.values())
            cands.append((libera - custo(chave, linhas), chave, linhas, tam))
        cands.sort(key=lambda x: -x[0])

        for _, chave, linhas, tam in cands:
            n = custo(chave, linhas)
            for v, t in tam.items():
                usado[lar[v]] -= t
            cabem = [k for k in range(len(cap)) if usado[k] + n <= cap[k][2]]
            # best-fit: o segmento mais APERTADO em que ainda cabe, para nao
            # gastar um segmento grande com uma string curta.
            i = min(cabem, key=lambda k: cap[k][2] - usado[k]) if cabem else None
            if i is None:                          # nao coube: desfaz, fica JP
                for v, t in tam.items():
                    usado[lar[v]] += t
                continue
            usado[i] += n
            prom.add(chave)
            for v in tam:
                lar[v] = i

        # o que nao foi promovido volta ao japones, no lugar onde ja' estava
        nao_prom = 0
        for chave, linhas in grupos.items():
            if isinstance(chave, tuple) or chave in prom:
                continue
            nao_prom += 1
            for r in linhas:
                r['traducao'] = '(verbatim)'

        vivos = sorted(set(lar.values()))
        for r in rs:
            va = int(r['va_string'], 16)
            k = lar.get(va)
            if k is None:                          # flutuante: sem sub-arena
                r['bloco'] = nome
                r['arena_ini'] = r['arena_fim'] = ''
                continue
            a, b, _ = cap[k]
            r['bloco'] = f'{nome}__s{vivos.index(k)+1}'
            r['arena_ini'] = f'0x{a:08X}'
            r['arena_fim'] = f'0x{b:08X}'

        tot_seg += len(vivos)
        falhou += nao_prom
        folga = sum(cap[k][2] - usado[k] for k in vivos)
        print(f'{nome}: {len(grupos)} strings distintas -> {len(vivos)} sub-arenas, '
              f'folga {folga:+d} B'
              + (f', {nao_prom} ficam em japones' if nao_prom else '')
              + (f', {len(flut)} fora de segmento' if flut else ''))
        for k in vivos:
            a, b, t = cap[k]
            print(f'   {nome}__s{vivos.index(k)+1}: 0x{a:08X}..0x{b:08X} = {t:>6} B, '
                  f'pool {usado[k]:>6} B, folga {t-usado[k]:+6d}')

    print(f'\ntotal: {tot_seg} sub-arenas'
          + (f', {falhou} strings sem espaco (ficam em japones)' if falhou else
             ', 0 strings perdidas'))

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    for p in args.csvs:
        cols, rows = arqs[p]
        if 'arena_ini' not in cols:
            cols = list(cols) + ['arena_ini', 'arena_fim']
        fica = [r for r in rows if not r.get('_dropar')]
        for r in fica:
            r.pop('_dropar', None)
            r.setdefault('arena_ini', '')
            r.setdefault('arena_fim', '')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            w.writerows(fica)
        print(f'-> {p}  ({len(rows)} -> {len(fica)} linhas)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

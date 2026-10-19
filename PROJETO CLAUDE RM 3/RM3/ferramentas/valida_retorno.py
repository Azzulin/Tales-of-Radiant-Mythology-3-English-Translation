#!/usr/bin/env python3
"""Valida o TSV que o tradutor devolve. Ver P-48.

Uso: valida_retorno.py <original.tsv> <retorno.tsv> [indice_nomes.csv] [--sem-largura]

RECUSA MECANICA — o lote volta inteiro se qualquer item falhar. Meia validacao
e' pior que nenhuma, porque parece completa.

Checa:
  E1  mesmo numero de linhas, mesmos `id`, mesma ordem
  E2  coluna `original` byte-identica a do arquivo enviado (ninguem editou a origem)
  E3  toda `traducao` preenchida
  E4  `traducao` em ASCII imprimivel (os marcadores OO, ▲▲, ▼▼ sao excecao)
  E5  control codes: mesma quantidade de `\\n`, `%s`, `%d` da origem
  E6  largura: nenhuma linha da traducao passa de 42 caracteres (P-33)
  E7  no maximo 3 linhas por fala (P-33)
  E8  japones residual na traducao = 0
  E9  consistencia de nome: se o indice de nomes for dado, um nome japones
      presente na origem tem de aparecer com a grafia adotada na traducao
  E10 consistencia interna: a MESMA origem em duas linhas tem de ter a MESMA
      traducao (a regra de ouro do projeto)
  E11 marcadores de substituicao em tempo real (OO nome do jogador — P-49; ▲▲/▼▼
      nome de item numa troca — P-63): mesma quantidade da origem cada um. Nao
      sao texto — o motor troca os bytes por conteudo escolhido/gerado
  E12 especificadores de printf (`%s`, `%d`, `% E`...): mesma sequencia e a
      MESMA ORDEM do japones, e nenhum criado onde o japones nao tem. A ordem
      e' a dos argumentos que o jogo empilhou, nao estilo (P-77.1)

`--sem-largura` desliga E6/E7. Elas medem a caixa de dialogo de 3x42 (P-33), que
so' vale para falas — texto de sistema do EBOOT (P-54) usa arena repontavel, sem
esse limite fisico. Fora isso o lote de sistema passa pelas mesmas dez regras.
"""
import sys, csv, re, unicodedata, collections

LARG_MAX = 42
LINHAS_MAX = 3
MARCA_ITEM_DE = '\u25b2\u25b2'    # triangulo-cima, item entregue numa troca (tev, P-63)
MARCA_ITEM_PARA = '\u25bc\u25bc'  # triangulo-baixo, item recebido numa troca (tev, P-63)
MARCADORES_ITEM = (MARCA_ITEM_DE, MARCA_ITEM_PARA)
# E12 (P-77.1): conversao de printf. O espaco e o '+' sao FLAGS, entao '% E'
# e '%+ E' tambem consomem argumento — nao basta olhar '%' colado na letra.
FORMATO = re.compile(r'%[-+ #0]*[0-9]*(?:\.[0-9]+)?(?:hh|h|ll|l|L|z|j|t)?[diouxXeEfgGaAcsp]')

MARCA_NOME = '\u25cb\u25cb'   # OO — marcador do nome do jogador (P-49). NAO e' texto:
                             # o motor troca estes 4 bytes EUC-JP pelo nome digitado.
                             # Constante de busca no EBOOT em 0x08CEE0F0.
SIMBOLOS_ENIGMA = ('\u2191', '\u2193', '\u2190', '\u2192', '\u25cb', '\u25cf', '\u21d2', '\u203b')  # setas e pistas de enigma (campo, P-65)
COLS_TRAVADAS = ('id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
                 'control_codes', 'original')


def le(p):
    fh = open(p, encoding='utf-8-sig', newline='')
    cab = fh.readline().rstrip('\r\n').split('\t')
    rows = []
    for ln, linha in enumerate(fh, 2):
        linha = linha.rstrip('\r\n')
        if not linha.strip():
            continue
        c = linha.split('\t')
        if len(c) < len(cab):
            c += [''] * (len(cab) - len(c))
        rows.append((ln, dict(zip(cab, c))))
    fh.close()
    return cab, rows


def katakana(c):
    return bool(c) and ('ァ' <= c <= 'ヶ' or c in 'ー・ｰ')


def hiragana(c):
    return bool(c) and ('ぁ' <= c <= 'ゖ' or c in 'ー・')


def kanji(c):
    return bool(c) and '一' <= c <= '鿿'


def jp(s):
    return [c for c in s if unicodedata.category(c) != 'Cc' and (
        '぀' <= c <= 'ヿ' or '一' <= c <= '鿿' or
        '！' <= c <= '｠' or '　' <= c <= '〿')]


def main():
    sem_largura = '--sem-largura' in sys.argv
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    orig_p, ret_p = pos[0], pos[1]
    nomes = {}
    if len(pos) > 2:
        for r in csv.DictReader(open(pos[2], encoding='utf-8')):
            if r.get('nome_jp') and r.get('nome_en'):
                nomes[r['nome_jp']] = r['nome_en']

    _, orig = le(orig_p)
    _, ret = le(ret_p)
    erros = []

    def E(cod, ln, msg):
        erros.append(f'{cod} linha {ln}: {msg}')

    if len(orig) != len(ret):
        erros.append(f'E1: {len(ret)} linhas no retorno, {len(orig)} no enviado')
    for (lo, o), (lr, r) in zip(orig, ret):
        if o['id'] != r.get('id'):
            E('E1', lr, f'id {r.get("id")!r}, esperado {o["id"]!r}')
            continue
        for c in COLS_TRAVADAS:
            if o.get(c, '') != r.get(c, ''):
                E('E2', lr, f'coluna travada `{c}` foi alterada: '
                            f'{r.get(c)!r} != {o.get(c)!r}')
        t = r.get('traducao', '')
        if not t.strip():
            E('E3', lr, 'traducao vazia'); continue
        # E11 — o marcador de nome do jogador e' control code, nao texto
        if o['original'].count(MARCA_NOME) != t.count(MARCA_NOME):
            E('E11', lr, f'marcador de nome do jogador: origem tem '
                         f'{o["original"].count(MARCA_NOME)}, traducao tem '
                         f'{t.count(MARCA_NOME)} — reproduza o mesmo numero')
        # E12 — especificador de printf: mesma sequencia, na MESMA ORDEM (P-77.1)
        # `%sのモンスターを%d匹` recebe primeiro um ponteiro, depois um inteiro.
        # Traduzir para `Defeat %d %s monsters!!` faz o `%d` ler o ponteiro como
        # numero e o `%s` ler o numero como endereco — lixo na tela ou crash.
        # A ordem nao e' estilo, e' a ordem dos argumentos que o jogo empilhou.
        fo, ft = FORMATO.findall(o['original']), FORMATO.findall(t)
        if fo != ft:
            if not fo:
                E('E12', lr, f'a traducao criou especificador de formato {ft} '
                             f'que o japones nao tem — em texto formatado por '
                             f'printf isso consome um argumento que nao existe. '
                             f'Escreva o "%" no fim, ou fora de "% letra"')
            else:
                E('E12', lr, f'especificadores de formato fora de ordem: '
                             f'japones {fo}, traducao {ft} — a ordem tem de ser '
                             f'identica, e' + ' a mesma dos argumentos do jogo')
        # mesma checagem para os marcadores de item (P-63) — tambem control code
        for marca, rotulo in ((MARCA_ITEM_DE, 'item entregue'), (MARCA_ITEM_PARA, 'item recebido')):
            if o['original'].count(marca) != t.count(marca):
                E('E11', lr, f'marcador de {rotulo} ({marca!r}): origem tem '
                             f'{o["original"].count(marca)}, traducao tem '
                             f'{t.count(marca)} — reproduza o mesmo numero')
        # para as demais checagens de ASCII, nenhum marcador conta
        t_sem = t.replace(MARCA_NOME, '')
        for marca in MARCADORES_ITEM:
            t_sem = t_sem.replace(marca, '')
        for simb in SIMBOLOS_ENIGMA:
            t_sem = t_sem.replace(simb, '')
        for ch in t_sem:
            if ch in '“”‘’—–…':
                E('E4', lr, f'caractere tipografico {ch!r} — use ASCII ("), (\'), (-), (...)')
                break
        try:
            t_sem.encode('ascii')
        except UnicodeEncodeError as ex:
            E('E4', lr, f'fora do ASCII: {ex.object[ex.start:ex.end]!r}')
        resto = jp(t_sem)
        if resto:
            E('E8', lr, f'japones residual na traducao: {"".join(resto[:8])!r}')
        for tok in ('%s', '%d'):
            if o['original'].count(tok) != t.count(tok):
                E('E5', lr, f'{tok}: origem tem {o["original"].count(tok)}, '
                            f'traducao tem {t.count(tok)}')
        if o['original'].count('\\n') != t.count('\\n'):
            E('E5', lr, f'quebras de linha: origem tem {o["original"].count(chr(92)+"n")}, '
                        f'traducao tem {t.count(chr(92)+"n")}')
        if o['original'].count('\\t') != t.count('\\t'):
            E('E5', lr, f'tabs: origem tem {o["original"].count(chr(92)+"t")}, '
                        f'traducao tem {t.count(chr(92)+"t")}')
        linhas = t.split('\\n')
        if not sem_largura:
            if len(linhas) > LINHAS_MAX:
                E('E7', lr, f'{len(linhas)} linhas, maximo {LINHAS_MAX}')
            for i, l in enumerate(linhas):
                if len(l) > LARG_MAX:
                    E('E6', lr, f'linha {i+1} tem {len(l)} caracteres, maximo {LARG_MAX}: {l[:50]!r}')
        for njp, nen in nomes.items():
            if len(njp) < 3 or any(parte in t for parte in nen.split()):
                continue
            # So conta como citacao se NAO for pedaco de uma sequencia kana maior:
            # `ティア` dentro de `バンエルティア` (Van Eltia) nao e' a Tear, e
            # `リオン` dentro de `アウリオン` (Aurion) nao e' o Leon (P-49); mesma
            # logica vale para nomes em hiragana — `しいな` dentro de `らしいな`
            # (particula de fim de frase) nao e' a Sheena. Nome em hiragana tambem
            # cola em kanji do lado (`欲しいな`, `嬉しいな` — final de i-adjetivo +
            # particula `な`, achado em P-55) e em katakana do lado (`ウラヤマしいな`
            # = "羨ましいな", i-adjetivo em katakana estilizado + `な`, achado em P-63):
            # kanji OU katakana vizinho tambem desqualifica um nome em hiragana.
            eh_katakana = any(katakana(c) for c in njp)
            eh_hiragana = any(hiragana(c) for c in njp)

            def limite(c):
                return ((eh_katakana and katakana(c)) or
                        (eh_hiragana and (hiragana(c) or kanji(c) or katakana(c))))

            for m in re.finditer(re.escape(njp), o['original']):
                antes = o['original'][m.start() - 1] if m.start() else ''
                depois = o['original'][m.end()] if m.end() < len(o['original']) else ''
                if limite(antes) or limite(depois):
                    continue
                E('E9', lr, f'origem cita `{njp}` mas a traducao nao usa `{nen.split()[0]}`')
                break

    # E10 — mesma origem, mesma traducao
    por = collections.defaultdict(set)
    for lr, r in ret:
        if r.get('original') and r.get('traducao', '').strip():
            por[r['original']].add(r['traducao'])
    for o, ts in por.items():
        if len(ts) > 1:
            erros.append(f'E10: a origem {o[:44]!r} recebeu {len(ts)} traducoes '
                         f'diferentes: {sorted(ts)[:3]}')

    n_checagens = 8 if sem_largura else 10
    print(f'{ret_p}: {len(ret)} linhas' + ('  (--sem-largura: E6/E7 desligadas)' if sem_largura else ''))
    if not erros:
        print(f'ACEITO — {n_checagens} de {n_checagens} checagens passaram')
        return 0
    cont = collections.Counter(e.split(':')[0].split()[0] for e in erros)
    print(f'RECUSADO — {len(erros)} falhas: {dict(cont)}')
    for e in erros[:60]:
        print('  ' + e)
    if len(erros) > 60:
        print(f'  ... e mais {len(erros)-60}')
    return 1


if __name__ == '__main__':
    sys.exit(main())

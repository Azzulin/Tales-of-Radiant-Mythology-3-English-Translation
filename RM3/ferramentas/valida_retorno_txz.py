#!/usr/bin/env python3
"""Valida o TSV que o tradutor devolve para um lote TXZ-XX (texto de quest, P-17).

Uso: valida_retorno_txz.py <TXZ-XX.tsv> <TXZ-XX_retorno.tsv>

Formato independente do `valida_retorno.py` (mev/cev/sis): aqui nao ha caixa de
dialogo 3x42, e SIM um teto de bytes Shift-JIS por linha (`orcamento_bytes`) que
substitui as checagens de largura. Ver `00_LEIA_PRIMEIRO_TXZ.md`.

RECUSA MECANICA — o lote volta inteiro se qualquer item falhar.

Checa:
  E1  mesmo numero de linhas, mesmos `id`, mesma ordem
  E2  colunas travadas (`id`, `arquivo`, `original`, `orcamento_bytes`)
      byte-identicas as do arquivo enviado
  E3  toda `traducao` preenchida
  E4  `traducao` em ASCII imprimivel (mesma logica/excecoes do `valida_retorno.py`
      para o marcador OO; alem dele, os tokens de controle desta frente `<...>`
      e `[...]` tambem escapam da checagem — sao control code, nao fala)
  E5  control codes desta frente preservados na mesma quantidade: `\\n` literal,
      marcadores `<...>`, tags de cor `[...]` (cada uma, e' o texto japones
      inteiro dentro do colchete que tem de bater, nao so' a contagem de
      colchetes) e o marcador de nome do jogador OO — mesmo mecanismo da R2 do
      pacote principal, tokens novos desta frente
  E8  japones residual na traducao = 0
  E10 consistencia interna: a MESMA origem em duas linhas tem de ter a MESMA
      traducao
  EB  NOVA E PRINCIPAL DESTA FRENTE: bytes Shift-JIS da `traducao` <=
      `orcamento_bytes` da mesma linha (P-17/P-19 — folga zero, offset fixo,
      sem ponteiro reponteavel)

Sem checagem de largura/numero de linhas de caixa de dialogo (nao se aplica a
esta frente — nao ha caixa 3x42 aqui).
"""
import sys
import csv
import re
import unicodedata
import collections

# console do Windows costuma vir em cp1252, que nao imprime japones residual nem
# travessao em relatorio de erro sem estourar; utf-8 com replace evita crash aqui
# sem mudar o resultado da validacao.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, ValueError):
    pass

MARCA_NOME = '○○'  # OO — marcador do nome do jogador, mesma convencao do resto do projeto
COLS_TRAVADAS = ('id', 'arquivo', 'original', 'orcamento_bytes')

RE_PLACEHOLDER = re.compile('＜[^＞]*＞')
RE_TAG = re.compile(r'\[[^\]]*\]')


def le(caminho):
    with open(caminho, encoding='utf-8-sig', newline='') as fh:
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
    return cab, rows


def jp(s):
    """Mesma faixa de deteccao de japones residual do valida_retorno.py."""
    return [c for c in s if unicodedata.category(c) != 'Cc' and (
        '぀' <= c <= 'ヿ' or '一' <= c <= '鿿' or
        '！' <= c <= '｠' or '　' <= c <= '〿')]


def controles(s):
    """Multiset dos tokens de controle desta frente: `\\n` literal, `<...>`,
    `[...]` e o marcador OO. Usado para E5 dos dois lados (origem e traducao)."""
    c = collections.Counter()
    c['\\n'] = s.count('\\n')
    c.update(RE_PLACEHOLDER.findall(s))
    c.update(RE_TAG.findall(s))
    if MARCA_NOME in s:
        c[MARCA_NOME] = s.count(MARCA_NOME)
    return c


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return 2
    orig_p, ret_p = args[0], args[1]

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
            E('E3', lr, 'traducao vazia')
            continue

        # E4 — ASCII imprimivel. Excecoes: OO (marcador de nome do jogador, igual
        # ao resto do projeto) e os tokens de controle desta frente (`<...>` e
        # `[...]`) — o texto japones dentro deles nao e' fala, e' parte do
        # control code (R2), tem de ficar identico ao original, nao virar ASCII.
        t_sem = t.replace(MARCA_NOME, '')
        t_sem = RE_PLACEHOLDER.sub('', t_sem)
        t_sem = RE_TAG.sub('', t_sem)
        for ch in t_sem:
            if ch in '“”‘’—–…':
                E('E4', lr, f'caractere tipografico {ch!r} — use ASCII ("), (\'), (-), (...)')
                break
        try:
            t_sem.encode('ascii')
        except UnicodeEncodeError as ex:
            E('E4', lr, f'fora do ASCII: {ex.object[ex.start:ex.end]!r}')

        # E5 — control codes desta frente, multiset origem == multiset traducao
        co = controles(o['original'])
        ct = controles(t)
        if co != ct:
            faltando = co - ct
            sobrando = ct - co
            partes = []
            if faltando:
                partes.append(f'faltando {dict(faltando)}')
            if sobrando:
                partes.append(f'a mais {dict(sobrando)}')
            E('E5', lr, 'control codes nao batem: ' + '; '.join(partes))

        # E8 — japones residual
        resto = jp(t_sem)
        if resto:
            E('E8', lr, f'japones residual na traducao: {"".join(resto[:8])!r}')

        # EB — orcamento de bytes Shift-JIS (a checagem nova e principal desta frente)
        try:
            orc = int(o.get('orcamento_bytes', ''))
        except ValueError:
            E('EB', lr, f'orcamento_bytes invalido na origem: {o.get("orcamento_bytes")!r}')
            orc = None
        if orc is not None:
            try:
                usados = len(t.encode('shift_jis'))
            except UnicodeEncodeError as ex:
                E('EB', lr, f'traducao nao codifica em Shift-JIS: {ex}')
                usados = None
            if usados is not None and usados > orc:
                E('EB', lr, f'traducao usa {usados} bytes Shift-JIS, orcamento e\' {orc} '
                             f'(estourou em {usados - orc})')

    # E10 — mesma origem, mesma traducao
    por = collections.defaultdict(set)
    for lr, r in ret:
        if r.get('original') and r.get('traducao', '').strip():
            por[r['original']].add(r['traducao'])
    for o, ts in por.items():
        if len(ts) > 1:
            erros.append(f'E10: a origem {o[:44]!r} recebeu {len(ts)} traducoes '
                         f'diferentes: {sorted(ts)[:3]}')

    print(f'{ret_p}: {len(ret)} linhas')
    if not erros:
        print('ACEITO — 8 de 8 checagens passaram (E1 E2 E3 E4 E5 E8 E10 EB)')
        return 0
    cont = collections.Counter(e.split(':')[0].split()[0] for e in erros)
    print(f'RECUSADO — {len(erros)} falhas: {dict(cont)}')
    for e in erros[:60]:
        print('  ' + e)
    if len(erros) > 60:
        print(f'  ... e mais {len(erros) - 60}')
    return 1


if __name__ == '__main__':
    sys.exit(main())

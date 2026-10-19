#!/usr/bin/env python3
"""Troca um termo ja' traduzido por outro em todos os lotes, so' na coluna
`traducao`, por palavra inteira (P-90).

Para decisao de grafia tomada DEPOIS de os lotes voltarem: `Apple Gummy` ->
`Apple Gel` (o nome oficial da franquia), e o que vier da auditoria de itens
recorrentes. A tabela de troca e' um TSV `de<TAB>para`, aplicado na ordem do
arquivo: ponha a forma mais longa antes (`Pine Gummy` antes de `Gummy`).

TSV (`.tsv`) e' tratado linha fisica por linha fisica, como no
`lote_restaura_marcador.py`, para nao mexer em mais nada do arquivo. CSV (`.csv`)
passa pelo modulo csv; a ferramenta confere que todas as outras colunas saem
identicas, campo a campo.

Dry-run por padrao; `--aplicar` grava e deixa `*.bak_pre_p90`.

Uso:
  lote_troca_termo.py <trocas.tsv> <arquivo>... [--sufixo .bak_pre_pNN] [--aplicar]

Regra `re:<regex><TAB><troca>`: expressao regular (P-95), sem fronteira automatica.
"""
import sys, re, csv, io, shutil, argparse

SUFIXO_BAK = '.bak_pre_p90'


def carrega_trocas(caminho):
    regras = []
    with open(caminho, encoding='utf-8') as f:
        for l in f:
            l = l.rstrip('\r\n')
            if not l or l.startswith('#'):
                continue
            de, para = l.split('\t')[:2]
            if de.startswith('re:'):
                # regra por expressao regular (P-95): sem fronteira de palavra
                # automatica; `para` aceita \\1. A quebra de linha chega como SEP
                regras.append((re.compile(de[3:]), para, de))
            else:
                regras.append((re.compile(r'(?<![A-Za-z])' + re.escape(de) + r'(?![A-Za-z])'), para, de))
    return regras


TOKEN_LF = chr(92) + 'n'          # a quebra de linha dos lotes: barra + n
SEP = chr(0)


def troca(texto, regras, cont):
    # o `n` do token de quebra nao pode contar como letra grudada no termo
    texto = texto.replace(TOKEN_LF, SEP)
    for rx, para, de in regras:
        texto, n = rx.subn(para, texto)
        cont[de] = cont.get(de, 0) + n
    return texto.replace(SEP, TOKEN_LF)


def processa_tsv(caminho, regras, cont):
    dado = open(caminho, 'rb').read().decode('utf-8')
    fim = '\r\n' if '\r\n' in dado else '\n'
    linhas = dado.split(fim)
    cab = linhas[0].lstrip('﻿').split('\t')
    if 'traducao' not in cab:
        return None, 0
    # 23 lotes CEV tem DUAS colunas `traducao` (identicas); o build le a ultima
    # (dict(zip(cab, linha))). Troca em todas, para nao divergirem (P-90).
    its = [i for i, x in enumerate(cab) if x == 'traducao']
    n = 0
    for k, l in enumerate(linhas[1:], 1):
        if not l:
            continue
        c = l.split('\t')
        mudou = False
        for it in its:
            if len(c) > it:
                novo = troca(c[it], regras, cont)
                if novo != c[it]:
                    c[it] = novo
                    mudou = True
        if mudou:
            linhas[k] = '\t'.join(c)
            n += 1
    return fim.join(linhas).encode('utf-8'), n


def processa_csv(caminho, regras, cont):
    dado = open(caminho, 'rb').read().decode('utf-8')
    fim = '\r\n' if '\r\n' in dado else '\n'
    linhas = list(csv.reader(io.StringIO(dado, newline='')))
    if not linhas or 'traducao' not in linhas[0]:
        return None, 0
    it = linhas[0].index('traducao')
    n = 0
    novas = [linhas[0]]
    for r in linhas[1:]:
        r2 = list(r)
        if len(r2) > it:
            novo = troca(r2[it], regras, cont)
            if novo != r2[it]:
                r2[it] = novo
                n += 1
        novas.append(r2)
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator=fim).writerows(novas)
    texto = out.getvalue()
    # confere: so' a coluna traducao mudou
    relido = list(csv.reader(io.StringIO(texto, newline='')))
    for a, b in zip(linhas, relido):
        if [x for i, x in enumerate(a) if i != it] != [x for i, x in enumerate(b) if i != it]:
            raise ValueError('%s: reescrever o CSV mudaria outra coluna' % caminho)
    return texto.encode('utf-8'), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('trocas')
    ap.add_argument('arquivos', nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    ap.add_argument('--sufixo', default=SUFIXO_BAK, help='sufixo do backup (padrao .bak_pre_p90)')
    a = ap.parse_args()
    regras = carrega_trocas(a.trocas)
    total = {}
    for p in a.arquivos:
        cont = {}
        fn = processa_csv if p.lower().endswith('.csv') else processa_tsv
        novo, n = fn(p, regras, cont)
        if novo is None:
            print('%s: sem coluna traducao, ignorado' % p)
            continue
        if n:
            print('%s: %d linha(s) — %s' % (p, n, ', '.join('%s x%d' % kv for kv in cont.items() if kv[1])))
        for k, v in cont.items():
            total[k] = total.get(k, 0) + v
        if a.aplicar and n:
            if not __import__('os').path.exists(p + a.sufixo):
                shutil.copy2(p, p + a.sufixo)
            open(p, 'wb').write(novo)
    print('\ntotal: ' + ', '.join('%s x%d' % kv for kv in total.items() if kv[1]))
    if not a.aplicar:
        print('DRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')


if __name__ == '__main__':
    sys.exit(main())

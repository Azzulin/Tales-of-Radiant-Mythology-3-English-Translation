#!/usr/bin/env python3
"""Devolve o marcador do nome do jogador (`○○`) onde o tradutor escreveu `OO` (P-83).

`○○` nao e' texto: o motor troca esses quatro bytes EUC-JP (a1fb a1fb) pelo nome
digitado pelo jogador (REGRAS_TRADUTOR.md, R2). Nos lotes de sinopse e de
capitulo o agente o transliterou para duas letras O maiusculas, e em jogo
aparece "OO" no lugar do nome.

So' troca quando nao ha' o que adivinhar: a linha tem N marcadores no original,
M na traducao, e exatamente N-M ocorrencias de `OO` isolado. Qualquer outra
divergencia e' listada e a linha fica como esta'.

Mexe so' na coluna `traducao`, linha fisica por linha fisica, para preservar o
resto do arquivo byte a byte (fim de linha, codigos de cor da sinopse).

Uso:
  lote_restaura_marcador.py <lote.tsv>... [--aplicar]
"""
import sys, re, shutil, argparse

MARCA = '○○'
OO = re.compile(r'\bOO\b')
SUFIXO_BAK = '.bak_pre_p83'


def processa(caminho):
    with open(caminho, 'rb') as f:
        dado = f.read()
    texto = dado.decode('utf-8')
    fim = '\r\n' if '\r\n' in texto else '\n'
    linhas = texto.split(fim)
    cab = linhas[0].split('\t')
    if 'original' not in cab or 'traducao' not in cab:
        return None, 0, []
    io, it = cab.index('original'), cab.index('traducao')
    trocadas, duvidas = 0, []
    for n, l in enumerate(linhas[1:], 1):
        if not l:
            continue
        c = l.split('\t')
        if len(c) != len(cab):
            raise ValueError('%s: linha %d tem %d colunas, cabecalho tem %d — '
                             'campo com quebra de linha?' % (caminho, n + 1, len(c), len(cab)))
        o, t = c[io], c[it]
        faltam = o.count(MARCA) - t.count(MARCA)
        if faltam <= 0:
            continue
        if len(OO.findall(t)) == faltam:
            c[it] = OO.sub(MARCA, t)
            linhas[n] = '\t'.join(c)
            trocadas += 1
        else:
            duvidas.append((n + 1, o[:40], t[:60]))
    return fim.join(linhas).encode('utf-8'), trocadas, duvidas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lotes', nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    total = 0
    for p in a.lotes:
        novo, n, duv = processa(p)
        if novo is None:
            print('%s: sem colunas original/traducao, ignorado' % p)
            continue
        print('%s: %d linha(s) corrigida(s), %d duvida(s)' % (p, n, len(duv)))
        for d in duv:
            print('   NAO MEXIDA linha %d: %r -> %r' % d)
        total += n
        if a.aplicar and n:
            shutil.copy2(p, p + SUFIXO_BAK)
            with open(p, 'wb') as f:
                f.write(novo)
    print('\ntotal: %d linha(s)' % total)
    if not a.aplicar:
        print('DRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')


if __name__ == '__main__':
    sys.exit(main())

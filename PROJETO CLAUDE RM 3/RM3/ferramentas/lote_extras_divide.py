#!/usr/bin/env python3
"""Separa um lote de "extras" em duas coisas que nao sao a mesma coisa (P-77).

`lote_extras_gera.py` varre uma arena nova e traz para o lote TUDO que e'
apontado ali dentro, marcando como `(verbatim)`, so' para a guarda 2 parar de
recusar. Mas ele mistura dois casos opostos:

  A. **Ponteiro a mais para uma string que o lote JA' traduz.** A mesma
     `va_string` aparece nos dois arquivos. Esse ponteiro TEM de entrar no
     build: a string vai mudar de lugar, e quem nao for reescrito fica lendo o
     que sobrou no endereco antigo. Aqui ele entra com a MESMA traducao, para
     deduplicar no pool (uma string, varios ponteiros — P-42.3).

  B. **String alheia de verdade**, que o lote nao traduz. Essa nao pode entrar.
     `(verbatim)` nao quer dizer "fica parada", quer dizer "viaja em japones":
     o build copia os bytes para o pool e reescreve o ponteiro. Para texto isso
     e' inocuo, mas as regioes do P-68 guardam `cl001.ppt`..`cl027.ppt`
     (arquivos DE VERDADE do `namco.bdi`, o modelo de cada classe) e
     `bgm017.at3`.. — 130 nomes de arquivo. Movidos de lugar, o jogo nao acha
     mais o recurso: tela preta depois da criacao de personagem. Elas ficam de
     fora do build e, com isso, viram barreira para `segmentos_livres`, que
     pica a arena em volta delas.

Uso:
  lote_extras_divide.py <extras.csv> <lote...> --saida <mantidos.csv> [--aplicar]
"""
import sys, os, csv, argparse, collections


def le(p):
    with open(p, encoding='utf-8') as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('extras')
    ap.add_argument('lotes', nargs='+')
    ap.add_argument('--saida', required=True)
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    trad = {}
    blo = {}
    for p in args.lotes:
        for r in le(p)[1]:
            if r['traducao'] and r['traducao'] != '(verbatim)':
                trad[int(r['va_string'], 16)] = r['traducao']
                blo[int(r['va_string'], 16)] = r['bloco']
    print(f'{len(trad)} strings traduzidas nos {len(args.lotes)} lotes')

    cols, rows = le(args.extras)
    mant, fora = [], []
    for r in rows:
        va = int(r['va_string'], 16)
        if va in trad:
            r['traducao'] = trad[va]
            r['bloco'] = blo[va]
            r['arena_ini'] = r['arena_fim'] = ''
            mant.append(r)
        else:
            fora.append(r)

    print(f'{args.extras}: {len(rows)} linhas')
    print(f'  A) {len(mant)} sao PONTEIRO A MAIS para string ja traduzida -> entram no build')
    print(f'  B) {len(fora)} sao string alheia de verdade -> ficam paradas, fora do build')
    cb = collections.Counter(r['bloco'] for r in mant)
    for b, c in cb.most_common(8):
        print(f'       A[{b}] {c}')

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    if 'arena_ini' not in cols:
        cols = list(cols) + ['arena_ini', 'arena_fim']
    with open(args.saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(mant)
    print(f'\n-> {args.saida}  ({len(mant)} linhas)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

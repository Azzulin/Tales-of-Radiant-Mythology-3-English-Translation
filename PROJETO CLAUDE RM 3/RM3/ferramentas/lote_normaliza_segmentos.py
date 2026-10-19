#!/usr/bin/env python3
"""Desfaz a segmentacao de um lote para que ela possa ser refeita do zero (P-74.1).

`item_equip_segmenta_arena.py` grava o resultado NO PROPRIO CSV: renomeia o
bloco para `<pai>__sN` e preenche `arena_ini`/`arena_fim`. Rodar o segmentador
de novo por cima disso nao recomeca — ele le `__s3` como se fosse um bloco-pai
chamado `__s3`, e as arenas velhas continuam valendo. O resultado e' um lote que
parece segmentado e nao esta, e o erro so' aparece na ISO.

Entao: antes de qualquer re-segmentacao, passar por aqui. Tira o sufixo `__sN`
e esvazia as duas colunas de arena, devolvendo o lote ao estado em que o
segmentador sabe le-lo.

O que NAO faz: nao desfaz FUSAO de bloco. `lote_funde_contidos.py` renomeou
`nomes_cidade` -> `ui` porque a arena de `ui` contem a de `nomes_cidade`
(P-72, passo 2); desfazer isso traria de volta a sobreposicao que a guarda 3
recusa. O nome do pai fica como esta.

Uso:
  lote_normaliza_segmentos.py <csv...> [--aplicar]
"""
import sys, csv, re, os, shutil, argparse

SUF = re.compile(r'__s\d+$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+')
    ap.add_argument('--sufixo-backup', default='.bak_pre_resegmenta')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    for p in args.csvs:
        with open(p, encoding='utf-8') as f:
            r = csv.DictReader(f)
            cols, rows = r.fieldnames, list(r)

        n_suf = n_ar = 0
        pais = {}
        for x in rows:
            b = x.get('bloco') or ''
            novo = SUF.sub('', b)
            if novo != b:
                n_suf += 1
                pais.setdefault(novo, set()).add(b)
                x['bloco'] = novo
            if x.get('arena_ini') or x.get('arena_fim'):
                n_ar += 1
                x['arena_ini'] = ''
                x['arena_fim'] = ''

        print(f'{p}: {len(rows)} linhas, {n_suf} com sufixo __sN, {n_ar} com arena')
        for pai, velhos in sorted(pais.items()):
            print(f'    {pai} <- {len(velhos)} segmentos')

        if not args.aplicar:
            continue
        bak = p + args.sufixo_backup
        if not os.path.exists(bak):
            shutil.copyfile(p, bak)
            print(f'    backup -> {bak}')
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        print(f'    -> {p}')

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

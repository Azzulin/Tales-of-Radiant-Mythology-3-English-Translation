#!/usr/bin/env python3
"""Gera o lote unico CAMPO-01 a partir de mapd_falantes.csv. Ver P-65.

Uso: gera_lote_campo.py <mapd_falantes.csv> <dir_saida>

`mapD`/`mapShip` juntos somam so' 124 falas (P-65) — cabe inteiro num lote so',
sem precisar da logica de corte por capitulo/grupo de `gera_lotes.py`/
`gera_lotes_nev.py`. Sem manifesto: um lote so' nao precisa de um CSV pra
rastrear ele mesmo.
"""
import sys, csv


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor']

    tsv_path = f'{dst}/CAMPO-01.tsv'
    with open(tsv_path, 'w', encoding='utf-8', newline='') as fh:
        fh.write('\t'.join(COLS) + '\n')
        for r in rows:
            campos = [r['id'], r['cena'], r['ordem'], r['falante'], r['falante'],
                      r['tipo'], r['control_codes'], r['original'], '', '']
            for c in campos:
                assert '\t' not in c and '\n' not in c, f'campo com TAB/LF em {r["id"]}'
            fh.write('\t'.join(campos) + '\n')

    cenas = sorted(set(r['cena'] for r in rows))
    tipos = {}
    for r in rows:
        tipos[r['tipo']] = tipos.get(r['tipo'], 0) + 1

    with open(f'{dst}/CAMPO-01.md', 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# CAMPO-01 — briefing\n\n')
        fh.write('| | |\n|---|---|\n')
        fh.write(f'| Falas | **{len(rows)}** |\n| Cenas | {len(cenas)} |\n')
        fh.write(f'| Bytes de japones | {sum(int(r["bytes_jp"]) for r in rows):,} |\n\n')
        fh.write('## Por tipo\n\n')
        for t, n in sorted(tipos.items(), key=lambda x: -x[1]):
            fh.write(f'- `{t}`: {n}\n')

    print(f'{len(rows)} falas, {len(cenas)} cenas -> {tsv_path}')


if __name__ == '__main__':
    main()

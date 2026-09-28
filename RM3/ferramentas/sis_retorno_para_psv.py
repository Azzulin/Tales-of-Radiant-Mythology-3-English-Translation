#!/usr/bin/env python3
"""Converte um ou mais SIS-NN_retorno.tsv (formato de eboot_lote_extrai.py)
para o .psv que lote_eboot.py espera (bloco|va_ponteiro|traducao|fonte|status|nota).

Uso: sis_retorno_para_psv.py <saida.psv> <SIS-01_retorno.tsv> [SIS-02_retorno.tsv ...]

Cada linha do TSV ja' representa uma string DEDUPLICADA (uma so' tradução para
todos os ponteiros que compartilham o mesmo japones original, ver P-54/P-42.3);
a coluna `va_ponteiros` traz todos esses enderecos separados por `;`. Este
script expande de volta para UMA linha de .psv por ponteiro — e' o que
lote_eboot.py precisa para reponteirar cada um deles para a mesma string.

Nao le nem escreve nenhum binario. So' texto.
"""
import sys, csv


def main():
    saida = sys.argv[1]
    fontes = sys.argv[2:]
    linhas = []
    for fn in fontes:
        rows = list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter='\t'))
        vazio = [r['id'] for r in rows if not r['traducao'].strip()]
        if vazio:
            print(f'RECUSADO: {fn} tem {len(vazio)} traducao(oes) vazia(s): {vazio[:5]}')
            return 1
        for r in rows:
            for vp in r['va_ponteiros'].split(';'):
                linhas.append({
                    'bloco': r['cena'],
                    'va_ponteiro': vp,
                    'traducao': r['traducao'],
                    'fonte': fn,
                    'status': 'validado',
                    'nota': r['nota_do_tradutor'],
                })
        print(f'{fn}: {len(rows)} strings distintas -> {sum(len(r2["va_ponteiros"].split(";")) for r2 in rows)} ponteiros')

    with open(saida, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('bloco|va_ponteiro|traducao|fonte|status|nota\n')
        for r in linhas:
            fh.write('|'.join(r[k] for k in ('bloco', 'va_ponteiro', 'traducao', 'fonte', 'status', 'nota')) + '\n')
    print(f'\n{len(linhas)} linhas -> {saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

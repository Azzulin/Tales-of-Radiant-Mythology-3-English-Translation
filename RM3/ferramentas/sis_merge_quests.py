#!/usr/bin/env python3
"""Gera o .psv completo do SIS-01+SIS-02, tratando a tabela fisica "quests"
(0x08D83230, 85 indices) como UMA arena so' -- o bloco `avisos` garimpa 16
desses indices e o `quests_sistema` os outros 68 (mais 1 ja ASCII, excluido na
extracao), e eboot_build2.py so' aceita bloco = arena real e disjunta (ver
PADROES_DESCOBERTOS.md P-61.6). Os 5 indices que `avisos` garimpa da tabela
"loja" (0x08D66818) formam um segundo bloco a parte, pequeno.

Uso: sis_merge_quests.py <saida.psv>
"""
import sys, csv

TABELA_QUESTS_INI = 0x08D83230
TABELA_QUESTS_FIM = TABELA_QUESTS_INI + 85 * 4  # exclusivo
INFO_VA = 0x08D8337C


def carrega(fn):
    return list(csv.DictReader(open(fn, encoding='utf-8-sig'), delimiter='\t'))


def main():
    saida = sys.argv[1]
    sis01 = carrega('../lotes/SIS-01_retorno.tsv')
    sis02 = carrega('../lotes/SIS-02_retorno.tsv')

    linhas = []

    def expande(rows, bloco_novo, fonte):
        for r in rows:
            for vp in r['va_ponteiros'].split(';'):
                linhas.append({
                    'bloco': bloco_novo, 'va_ponteiro': vp,
                    'traducao': r['traducao'], 'fonte': fonte,
                    'status': 'validado', 'nota': r['nota_do_tradutor'],
                })

    for r in sis01:
        if r['cena'] == 'avisos':
            algum_vp = int(r['va_ponteiros'].split(';')[0], 16)
            if TABELA_QUESTS_INI <= algum_vp < TABELA_QUESTS_FIM:
                expande([r], 'quests_completo', 'SIS-01#avisos(quests)')
            else:
                expande([r], 'loja_avisos', 'SIS-01#avisos(loja)')
        else:
            expande([r], r['cena'], 'SIS-01')

    for r in sis02:
        expande([r], 'quests_completo', 'SIS-02')

    linhas.append({
        'bloco': 'quests_completo', 'va_ponteiro': f'0x{INFO_VA:08X}',
        'traducao': '', 'fonte': 'ja-ascii', 'status': 'validado',
        'nota': 'Information, ja em ingles, mantido verbatim',
    })

    with open(saida, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('bloco|va_ponteiro|traducao|fonte|status|nota\n')
        for r in linhas:
            fh.write('|'.join(r[k] for k in ('bloco', 'va_ponteiro', 'traducao', 'fonte', 'status', 'nota')) + '\n')

    por_bloco = {}
    for r in linhas:
        por_bloco[r['bloco']] = por_bloco.get(r['bloco'], 0) + 1
    for b, n in por_bloco.items():
        print(f'  {b}: {n} ponteiros')
    print(f'\n{len(linhas)} linhas -> {saida}')


if __name__ == '__main__':
    main()

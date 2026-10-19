#!/usr/bin/env python3
"""Divide o bloco `elenco_hud_batalha` de sis04.psv em dois blocos reais,
por endereco fisico de string. Ver P-67.

`lote_eboot.py` tratou as 234 entradas de `elenco_hud_batalha` como UMA arena
so' (min..max dos va_string = 34.991 B), porque o calculo ingenuo de
min/max nao sabe que os dados moram em DOIS agrupamentos fisicos distintos e
disjuntos: nomes/comandos de batalha (0x08D05F64..0x08D06778, ~2KB) e
rotulos de categoria de quest/equipamento (0x08D0E408..0x08D0E810, ~1KB) —
um buraco de quase 32KB de conteudo NAO relacionado no meio (outras tabelas
do EBOOT). Construir isso como um bloco so' zeraria/sobrescreveria esse
buraco inteiro. Oposto do merge de SIS-03 (P-66: 11 blocos que pareciam
separados eram UMA arena so'); aqui uma tabela que parecia uma arena so' era
DUAS, seria pego pela guarda 2 do eboot_build2.py se nao corrigido antes.

Uso: sis04_split_elenco.py <eboot_dec> <sis04.psv> <saida.psv>

Resolve va_string direto no binario (nao depende de auditoria previa) —
seguro rodar de novo a qualquer momento, mesmo depois de reencurtar traducao.
"""
import sys, csv
import eboot_tabsis as T

CORTE = 0x08D07000  # abaixo = elenco_hud_nomes, acima = elenco_hud_labels

# 3 ponteiros da MESMA tabela fisica (idx 1/3, 2/3, 3/3 de 'elenco_hud_batalha')
# que `eboot_lote_extrai.py` pula por ja serem ASCII puro (nada a traduzir) —
# mas o ponteiro continua existindo de verdade e apontando pra dentro da arena
# de `elenco_hud_labels`. Nao entram no .psv vindo do retorno do tradutor
# (nunca foram pedidos pra traduzir), soh' aqui, verbatim, pra guarda 2 do
# eboot_build2.py nao os achar "de fora" (mesmo padrao do INFO_VA em
# sis_merge_quests.py).
VERBATIM_EXTRA = {
    'elenco_hud_labels': ['0x08D83674', '0x08D83678', '0x08D8367C'],
}


def main():
    eb, psv, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    d = T.ler(eb)

    with open(psv, encoding='utf-8') as fh:
        cab = fh.readline().rstrip('\n')
        linhas = [l.rstrip('\n') for l in fh if l.strip()]

    cols = cab.split('|')
    i_bloco = cols.index('bloco')
    i_vp = cols.index('va_ponteiro')
    out = [cab]
    cont = {}
    for l in linhas:
        c = l.split('|')
        if c[i_bloco] == 'elenco_hud_batalha':
            vp = int(c[i_vp], 16)
            e = T.entradas(d, vp, 1)[0]
            novo = 'elenco_hud_nomes' if e['va_string'] < CORTE else 'elenco_hud_labels'
            c[i_bloco] = novo
        else:
            novo = c[i_bloco]
        cont[novo] = cont.get(novo, 0) + 1
        out.append('|'.join(c))

    for bloco, ponteiros in VERBATIM_EXTRA.items():
        for vp in ponteiros:
            out.append(f'{bloco}|{vp}||ja-ascii|validado|ja e ASCII, mantido verbatim')
            cont[bloco] = cont.get(bloco, 0) + 1

    with open(saida, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')

    for b, n in cont.items():
        print(f'  {b}: {n} ponteiros')
    print(f'-> {saida}')


if __name__ == '__main__':
    main()

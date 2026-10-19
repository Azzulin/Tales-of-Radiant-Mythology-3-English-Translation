#!/usr/bin/env python3
"""Funde 11 dos 12 blocos de SIS-03 (banner de area) que compartilham a MESMA
arena fisica de string, contra a suposicao inicial de 12 arenas independentes
(uma por regiao). Ver P-66.

`lote_eboot.py` audita SIS-03 tratando cada `cena` (nome de regiao) como o seu
proprio bloco/arena. Conferido byte a byte: `elan_vital` tem mesmo arena
propria e disjunta (0x08C60DF8..0x08C60F35). As outras 11 regioes
(rhubarb/brownie/shifuno/ortera/langrisse/veratropa/confeito/almanac/
reminiscencia/kadaif/absoule) compartilham UMA string pool so'
(0x08C60F38..0x08C61FF7) — strings repetidas entre regioes (ex.
`光の幾何学場`/"Geometry of Light", usada por 9 das 11) sao internadas UMA vez
so' e reaproveitadas por ponteiros de regioes diferentes. Tratar cada regiao
como arena propria faz `rhubarb` estourar (a arena aparente de 267B e' na
verdade so' um pedaco da pool de ~4.3KB real) e faria `eboot_build2.py` recusar
por sobreposicao de arena entre as outras 10. Mesmo padrao do P-62.1
(`sis_merge_quests.py`): juntar em UM bloco so' faz o dedup functionar
corretamente entre regioes, nao so' dentro de uma.

Uso: sis03_merge_areas.py <sis03.psv> <saida.psv>
"""
import sys

SEPARADA = {'elan_vital'}
NOME_MERGE = 'banners_area'


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding='utf-8') as fh:
        cab = fh.readline().rstrip('\n')
        linhas = [l.rstrip('\n') for l in fh if l.strip()]

    cols = cab.split('|')
    i_bloco = cols.index('bloco')
    out = [cab]
    cont = {}
    for l in linhas:
        c = l.split('|')
        bloco = c[i_bloco]
        novo = bloco if bloco in SEPARADA else NOME_MERGE
        cont[novo] = cont.get(novo, 0) + 1
        c[i_bloco] = novo
        out.append('|'.join(c))

    with open(dst, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(out) + '\n')

    for b, n in cont.items():
        print(f'  {b}: {n} ponteiros')
    print(f'-> {dst}')


if __name__ == '__main__':
    main()

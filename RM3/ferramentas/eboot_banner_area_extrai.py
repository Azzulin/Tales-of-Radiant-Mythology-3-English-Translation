#!/usr/bin/env python3
"""Extrai os nomes de área/sala/trecho do banner de mapa (P-63.3/63.6) para lote.

Uso: eboot_banner_area_extrai.py <eboot_dec> <saida.tsv>

Formato descoberto na sessao de 18/09: 13 tabelas de REGISTRO FIXO DE 20 BYTES em `.data`, uma por
regiao de `nomes_masmorra_viagem` (P-54.4) MAIS uma 13a tabela, `spectrum` (P-66), achada so' na
sessao de 21/09 ao rodar `eboot_build2.py` (guarda 2 recusou ponteiros de fora apontando pra
dentro da arena de `SIS-03` — nao era outra tabela sobrando, era esta faltando). Nao e' o
`闘技場`/Arena (esse continua sem sub-area, sem tabela). Cada registro:

    +0  u32  ponteiro da string (EUC-JP/Shift-JIS, NUL-terminada, em .rodata)
    +4  u32  id (sequencial dentro da tabela, funcao exata nao decifrada)
    +8  u32  ponteiro secundario (funcao nao decifrada)
    +12 u32  contagem pequena (funcao nao decifrada)
    +16 u32  flags (funcao nao decifrada)

A teoria de "ultimo registro de cada tabela e' um RODAPE" (`ponteiro_secundario == 0x000E0001`)
foi PROPOSTA em P-63.6 e DERRUBADA em P-63.7 (0 rodapes de verdade em nenhuma das 12 tabelas
originais, nem na 13a) — o codigo abaixo mantem a checagem como rede de seguranca (nunca fez mal
nenhuma vez, so' nunca disparou), nao porque a teoria seja verdadeira.

So' a STRING (+0) e traduzida — os outros 4 campos ficam preservados em colunas extras no `.tsv`
(fora do padrao MEV, ignoradas pelo validador, mesma convencao de `va_ponteiros`/`ocorrencias` em
`eboot_lote_extrai.py`) para quando a ferramenta de reinsercao for escrita: só o ponteiro da
string muda, o resto do registro de 20 bytes fica como está.

Dedup por string identica DENTRO da mesma regiao (mesma logica de P-42.3/P-54); nao dedup ENTRE
regioes -- duas regioes diferentes usando a mesma palavra (ex. "入口"/entrada) sao contextos
fisicamente distintos e viram pontos de repontamento independentes.

Somente leitura no binario.
"""
import sys, csv, struct

RODAPE_SECUNDARIO = 0x000E0001

# nome da regiao -> (vaddr do 1o registro, contagem TOTAL de registros, incluindo o rodape)
# enderecos e contagens de P-63.6, cada um reconferido direto no binario nesta sessao ou na
# investigacao anterior; nomes_masmorra_viagem/quadro (P-54.4) tem a grafia japonesa de cada uma.
# `absoule` corrigido e `spectrum` acrescentada em P-66 (21/09) — as 2 primeiras entradas de
# absoule e a tabela `spectrum` inteira nao apareciam no levantamento original.
TABELAS = {
    'rhubarb':        (0x08D5E9C4, 24),
    'elan_vital':     (0x08D5E508, 32),
    'brownie':        (0x08D5F204, 30),
    'shifuno':        (0x08D60C50, 26),
    'ortera':         (0x08D5F674, 22),
    'langrisse':      (0x08D61040, 20),
    'veratropa':      (0x08D607D0, 17),
    'confeito':       (0x08D5ED2C, 16),
    'almanac':        (0x08D5FFE4, 15),
    'reminiscencia':  (0x08D62104, 60),
    'kadaif':         (0x08D5FB88, 35),
    'absoule':        (0x08D60400, 24),
    'spectrum':       (0x08D618A4, 37),
}

DELTA = 0x08803000  # fileoff -> vaddr, mesma constante de eboot_build2.py (P-42.4)


def decodifica(b):
    try:
        return b.decode('euc_jp')
    except UnicodeDecodeError:
        return b.decode('shift_jis')


def eh_ascii_puro(s):
    try:
        s.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def le_registro(data, va):
    off = va - DELTA
    ptr_str, campo_id, ptr_sec, contagem, flags = struct.unpack_from('<5I', data, off)
    p = ptr_str - DELTA
    z = data.find(b'\x00', p)
    jp = decodifica(data[p:z])
    return {'ptr_string': ptr_str, 'id': campo_id, 'ptr_secundario': ptr_sec,
            'contagem': contagem, 'flags': flags, 'original': jp}


def main():
    eb, saida = sys.argv[1], sys.argv[2]
    data = open(eb, 'rb').read()

    linhas = []
    pulados = []
    resumo = []
    for regiao, (va0, n) in TABELAS.items():
        vistos = {}
        ordem = 0
        n_rodape = 0
        for i in range(n):
            va = va0 + i * 20
            r = le_registro(data, va)
            if r['ptr_secundario'] == RODAPE_SECUNDARIO:
                n_rodape += 1
                continue
            jp = r['original']
            if eh_ascii_puro(jp):
                pulados.append(f'{regiao} 0x{va:08X}: ja e ASCII ({jp!r}), nada a traduzir')
                continue
            if jp in vistos:
                vistos[jp]['va_ponteiros'].append(f'0x{va:08X}')
                continue
            row = {
                'id': f'{regiao}#{ordem}', 'cena': regiao, 'ordem': ordem,
                'falante_jp': '(banner de area)', 'falante_en': '(area banner)',
                'tipo': 'sistema', 'control_codes': '',
                'original': jp, 'traducao': '', 'nota_do_tradutor': '',
                'va_ponteiros': [f'0x{va:08X}'],
                'campo_id': f'0x{r["id"]:08X}', 'ponteiro_secundario': f'0x{r["ptr_secundario"]:08X}',
                'contagem_reg': r['contagem'], 'flags_reg': f'0x{r["flags"]:08X}',
            }
            vistos[jp] = row
            linhas.append(row)
            ordem += 1
        resumo.append((regiao, n, n_rodape, len(vistos)))

    for r in linhas:
        r['ocorrencias'] = len(r['va_ponteiros'])
        r['va_ponteiros'] = ';'.join(r['va_ponteiros'])

    cols = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo', 'control_codes',
            'original', 'traducao', 'nota_do_tradutor', 'va_ponteiros', 'ocorrencias',
            'campo_id', 'ponteiro_secundario', 'contagem_reg', 'flags_reg']
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter='\t')
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'{len(linhas)} linhas para traduzir -> {saida}\n')
    print(f'{"regiao":<16}{"registros":>10}{"rodapes":>9}{"distintas":>11}')
    for regiao, n, rod, dist in resumo:
        print(f'{regiao:<16}{n:>10}{rod:>9}{dist:>11}')
    if pulados:
        print(f'\npulados ({len(pulados)}), nao entram no lote:')
        for p in pulados:
            print('  ' + p)
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Acha, por FORCA BRUTA, todo ponteiro que referencia cada string do banco de
item/equipamento, e monta o `.csv` no formato que `eboot_build2.py` espera
(P-67.9/67.10).

Diferenca chave do metodo de sempre (`lote_eboot.py`, que le um array de
ponteiro CONTIGUO via `eboot_tabsis.entradas()`): aqui os ponteiros vivem
DENTRO de registros de tamanho fixo, com campos nao-ponteiro no meio (ou, no
caso de `valuables`, uma mistura de array puro + registro — ver P-67.9). Em
vez de assumir QUALQUER layout, procura o VA de CADA string (todas as
ocorrencias, nao so' a primeira — uma mesma string pode ter `ptr_nome` E
`ptr_nome_dup` apontando pra ela) como 4 bytes crus em TODO o binario. Mesmo
metodo que achou o formato de `consumivel`/`head_equip` em P-67.3, e que
confirmou os outros 32 registros em P-67.9 — aqui aplicado string a string,
sem precisar decifrar o layout de registro de cada categoria (funciona igual
pra `valuables`, que nao tem stride unico).

Uso: item_equip_ponteiros.py <eboot_dec> [--falantes CSV] [--lotes GLOB] [--saida CSV]

Depois de gerar o `.csv`, RODAR `item_equip_pontos_sanidade.py` nele antes de
passar pro `eboot_build2.py` — a busca cega tem uma chance pequena (mas nao
zero) de casar um VA por coincidencia num lugar que nao e' realmente uma
tabela de ponteiro.
"""
import sys, csv, struct, glob, argparse, json, os

DELTA = 0x08803000


def unescape(t):
    return t.replace('\\r\\n', '\r\n').replace('\\n', '\n').replace('\\t', '\t')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--falantes', default='dados/item_equip_falantes.tsv')
    ap.add_argument('--lotes', default='lotes/ITEM-*_retorno.tsv')
    ap.add_argument('--saida', default='dados/item_equip_ponteiros.csv')
    ap.add_argument('--encurtamentos', nargs='*',
                    default=['dados/item_equip_shrink/FINAL_encurtamentos.json',
                             'dados/item_equip_correcoes.json'],
                    help='JSONs {id: traducao} que sobrepoem o lote, na ordem dada: '
                         'encurtamento para caber na arena (P-67.11) e correcao de '
                         'glossario achada por valida_lotes.py (P-68.2). Opcional.')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    with open(args.falantes, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))

    traducoes = {}
    for path in sorted(glob.glob(args.lotes)):
        with open(path, encoding='utf-8') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                traducoes[row['id']] = row['traducao']

    for caminho in (args.encurtamentos or []):
        if not os.path.exists(caminho):
            continue
        with open(caminho, encoding='utf-8') as f:
            over = json.load(f)
        usadas = sum(1 for k in over if k in traducoes)
        traducoes.update({k: v for k, v in over.items() if k in traducoes})
        print(f'{usadas} traducoes sobrepostas por {caminho}')

    faltando = [r['id'] for r in rows if r['id'] not in traducoes]
    if faltando:
        print(f'ERRO: {len(faltando)} strings sem traducao (ex: {faltando[:5]})')
        return 2

    saida_rows = []
    sem_ponteiro = []
    for row in rows:
        cena = row['cena']
        original_bruto = unescape(row['original'])
        bytes_jp = len(original_bruto.encode('euc_jp'))
        trad = traducoes[row['id']]
        vas = [int(v, 16) for v in row['va_strings'].split(';')]
        achou = 0
        for va in vas:
            pat = struct.pack('<I', va)
            p = 0
            while True:
                i = raw.find(pat, p)
                if i == -1:
                    break
                achou += 1
                saida_rows.append({
                    'bloco': cena,
                    'va_ponteiro': f'0x{i + DELTA:08X}',
                    'va_string': f'0x{va:08X}',
                    'bytes_jp': bytes_jp,
                    'traducao': trad,
                    'id': row['id'],
                    'original': row['original'],
                })
                p = i + 1
        if achou == 0:
            sem_ponteiro.append(row['id'])

    cols = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'id', 'original']
    with open(args.saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in saida_rows:
            w.writerow(r)

    print(f'{len(rows)} strings  ->  {len(saida_rows)} ponteiros achados  ->  {args.saida}')
    print(f'{len(sem_ponteiro)} strings SEM nenhum ponteiro achado (nao vao pro build)')
    if sem_ponteiro:
        print('  ids:', ', '.join(sem_ponteiro[:20]), '...' if len(sem_ponteiro) > 20 else '')
    return 0


if __name__ == '__main__':
    sys.exit(main())

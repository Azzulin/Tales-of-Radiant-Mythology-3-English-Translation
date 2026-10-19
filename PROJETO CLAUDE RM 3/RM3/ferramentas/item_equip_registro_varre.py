#!/usr/bin/env python3
"""Varre TODAS as categorias do banco de item/equipamento tentando achar o
stride (tamanho de registro) de cada uma, pelo mesmo metodo de forca bruta
usado individualmente em item_equip_registro_sonda.py (P-67.8/67.9).

So' leitura, so' relatorio — nao decide nada sozinho. Pra cada categoria:
pega as primeiras N strings distintas (ordem crescente == ordem de varredura
da arena), acha o MENOR offset onde cada uma aparece como ponteiro cru de 4
bytes em QUALQUER lugar do EBOOT, e mede a diferenca entre esses offsets
consecutivos. Se essa sequencia de diferencas for PERIODICA (um padrao curto
se repetindo: ex. 8,44,8,44,8,44...), a soma de um periodo completo e' o
stride candidato. Reporta o candidato e a confianca (quantos periodos
completos bateram exatamente).

Uso: item_equip_registro_varre.py <eboot_dec> [--n N] [--falantes CSV]
"""
import sys, csv, struct, argparse, collections

DELTA = 0x08803000


def menores_offsets(raw, vas):
    out = []
    for va in vas:
        pat = struct.pack('<I', va)
        i = raw.find(pat)
        out.append(i)  # -1 se nao achou
    return out


def detecta_stride(deltas):
    """deltas: lista de diferencas entre offsets consecutivos (>=0, inteiros).
    Tenta achar o MENOR periodo P (1..6) tal que as janelas NAO sobrepostas
    soma(deltas[i*P:(i+1)*P]) concordem na maioria (>=60%) com o valor mais
    comum. Retorna (periodo, stride, 'bate/total') ou (None, None, '-').
    """
    n = len(deltas)
    for periodo in range(1, 7):
        total = n // periodo
        if total < 3:
            continue
        somas_passo = [sum(deltas[i * periodo:(i + 1) * periodo]) for i in range(total)]
        contagem = collections.Counter(somas_passo)
        alvo, bate = contagem.most_common(1)[0]
        if alvo > 0 and bate / total >= 0.6:
            return periodo, alvo, f'{bate}/{total}'
    return None, None, '-'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--falantes', default='dados/item_equip_falantes.tsv')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    with open(args.falantes, encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter='\t')
        todas = list(r)

    categorias = []
    vistos = set()
    for row in todas:
        if row['cena'] not in vistos:
            vistos.add(row['cena'])
            categorias.append(row['cena'])

    print(f'{"categoria":<18}{"strings":>8}  {"periodo":>7}{"stride":>8}{"confianca":>10}  padrao-de-delta')
    for cat in categorias:
        sub = [row for row in todas if row['cena'] == cat]
        sub.sort(key=lambda x: int(x['ordem']))
        sub = sub[:args.n]
        vas = [int(row['va_strings'].split(';')[0], 16) for row in sub]
        offs = menores_offsets(raw, vas)
        pares = [(o) for o in offs if o != -1]
        if len(pares) < 4:
            print(f'{cat:<18}{len(sub):>8}  poucas ocorrencias achadas ({len(pares)}) — sondar individualmente')
            continue
        deltas = [pares[i + 1] - pares[i] for i in range(len(pares) - 1)]
        periodo, stride, conf = detecta_stride(deltas)
        padrao = ','.join(str(d) for d in deltas[:periodo]) if periodo else '?'
        print(f'{cat:<18}{len(sub):>8}  {periodo!s:>7}{stride!s:>8}{conf:>10}  [{padrao}]  deltas={deltas[:10]}')

    return 0


if __name__ == '__main__':
    sys.exit(main())

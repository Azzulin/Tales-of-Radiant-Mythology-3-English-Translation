#!/usr/bin/env python3
"""Funde o bloco `itens` (P-54, `sis_auditoria.csv`) dentro de `valuables`
(P-67.9, banco de item/equipamento) — P-67.11.

O problema: as 224 strings do bloco `itens` sao um SUBCONJUNTO exato das 2.608
de `valuables` (0 strings so' em `itens`), e a faixa de `itens`
(0x08CA44C0..0x08CA5D94) cai DENTRO da arena de `valuables`
(0x08CA3ED8..0x08CBCCC4). A guarda 3 de `eboot_build2.py` recusa, com razao:
dois blocos nao podem reivindicar a mesma memoria — o pool de um seria escrito
por cima do outro.

Mesmo caso do P-62.1 (`avisos` + `quests_sistema` -> `quests_completo`), e a
saida e' a mesma: um bloco so'. Como `itens` nao tem nenhuma string propria,
funde-se ELE em `valuables` e o bloco `itens` deixa de existir.

Qual traducao vence nas 136 strings em que os dois lotes divergem, e' escolha
de traducao, nao de build — daí' `--precedencia`:

  producao  (padrao) a traducao de `itens`, ja' validada 10/10 e em jogo desde
                     o `en08`. Zero retrocesso. Mantem `Koda`.
  novo               a traducao de `valuables` (agente externo, 09/2026).
  producao-corrigido `producao`, mas com os nomes proprios do lote novo onde o
                     lote antigo contraria o INDICE_NOMES (`Koda` -> `Coda`).

Uso:
  item_equip_funde_itens.py dados/sis_auditoria.csv dados/item_equip_ponteiros_limpo.csv \\
      [--precedencia producao|novo|producao-corrigido] [--aplicar]

Sem `--aplicar` so' relata. Com `--aplicar`, reescreve os dois CSVs: tira as
linhas do bloco `itens` do primeiro e, se a precedencia mandar, troca a
traducao das linhas correspondentes de `valuables` no segundo.
"""
import sys, csv, argparse, collections

# nomes proprios em que o lote antigo contraria o INDICE_NOMES (P-67.11)
CORRIGE = {'Koda': 'Coda'}


def le(path):
    with open(path, encoding='utf-8') as f:
        leitor = csv.DictReader(f)
        return leitor.fieldnames, list(leitor)


def escreve(path, cols, rows):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sis_csv')
    ap.add_argument('valuables_csv')
    ap.add_argument('--bloco-antigo', default='itens')
    ap.add_argument('--bloco-novo', default='valuables')
    ap.add_argument('--precedencia', default='producao',
                    choices=['producao', 'novo', 'producao-corrigido'])
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    cols_s, rows_s = le(args.sis_csv)
    cols_v, rows_v = le(args.valuables_csv)

    antigos = [r for r in rows_s if (r.get('bloco') or '') == args.bloco_antigo]
    if not antigos:
        print(f'nada a fazer: bloco {args.bloco_antigo} nao esta em {args.sis_csv}')
        return 0
    trad_antiga = {int(r['va_string'], 16): r['traducao'] for r in antigos}

    novos = [r for r in rows_v if r['bloco'] == args.bloco_novo]
    vas_novos = {int(r['va_string'], 16) for r in novos}

    orfas = set(trad_antiga) - vas_novos
    if orfas:
        print(f'RECUSADO: {len(orfas)} strings de {args.bloco_antigo} nao existem '
              f'em {args.bloco_novo} — a fusao perderia traducao ja em producao')
        for v in sorted(orfas)[:10]:
            print(f'  0x{v:08X} {trad_antiga[v][:50]!r}')
        return 1
    print(f'{len(trad_antiga)} strings de `{args.bloco_antigo}` sao subconjunto de '
          f'`{args.bloco_novo}` (0 orfas)  OK')

    divergem = [r for r in novos
                if int(r['va_string'], 16) in trad_antiga
                and trad_antiga[int(r['va_string'], 16)] != r['traducao']]
    print(f'{len(divergem)} ponteiros com traducao divergente entre os dois lotes')

    trocados = corrigidos = 0
    if args.precedencia in ('producao', 'producao-corrigido'):
        for r in novos:
            va = int(r['va_string'], 16)
            if va not in trad_antiga:
                continue
            t = trad_antiga[va]
            if args.precedencia == 'producao-corrigido':
                for errado, certo in CORRIGE.items():
                    if errado in t:
                        t = t.replace(errado, certo)
                        corrigidos += 1
            if r['traducao'] != t:
                r['traducao'] = t
                trocados += 1
        print(f'precedencia `{args.precedencia}`: {trocados} traducoes de '
              f'`{args.bloco_novo}` trocadas pela versao em producao')
        if corrigidos:
            print(f'  ({corrigidos} com nome proprio corrigido: '
                  f'{", ".join(f"{k}->{v}" for k, v in CORRIGE.items())})')
    else:
        print(f'precedencia `novo`: mantida a traducao do lote novo '
              f'({len(divergem)} divergencias)')

    restantes = [r for r in rows_s if (r.get('bloco') or '') != args.bloco_antigo]
    print(f'bloco `{args.bloco_antigo}` removido de {args.sis_csv}: '
          f'{len(rows_s)} -> {len(restantes)} linhas')

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    escreve(args.sis_csv, cols_s, restantes)
    escreve(args.valuables_csv, cols_v, rows_v)
    print(f'-> {args.sis_csv}\n-> {args.valuables_csv}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

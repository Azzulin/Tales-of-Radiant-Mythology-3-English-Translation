#!/usr/bin/env python3
"""Filtra `item_equip_ponteiros.csv` antes do build (P-67.10).

A busca cega de `item_equip_ponteiros.py` acha, pra cada string, TODO lugar
onde o VA dela aparece como 4 bytes crus — a maioria e' ponteiro de verdade,
mas uma fatia pequena e' colisao por coincidencia (um valor de 32 bits que
por acaso bate com aquele endereco, em um lugar do binario que nao tem nada
a ver com o banco de item/equipamento).

Regra usada pra separar: toda categoria tem sua faixa de VA conhecida (a
mesma faixa `CATEGORIAS`/`FIM_ULTIMA` de `item_equip_extrai.py`, ja' que a
propria string sentinela `無効値（categoria）` marca o inicio de cada uma).
- ponteiro caindo DENTRO de QUALQUER categoria (a dele ou de outra) -> fica.
  Texto compartilhado entre categorias existe de verdade (achado: uma
  descricao generica de "arma de treino" reaproveitada em `sword_1h`,
  `sword_2h`, `axe`, `dagger`, `staff`, `fist`, `bow`, `handgun` — 7
  categorias apontando pro MESMO texto fisico) — bloco continua sendo o da
  categoria ONDE O TEXTO VIVE (`eboot_build2.py` so' usa `bloco` pra agrupar
  a arena da STRING, nao liga pra onde o campo de ponteiro fisicamente
  mora).
- ponteiro caindo FORA de toda faixa conhecida -> colisao, descartado.

Depois de filtrar, avisa se alguma string ficou com ZERO ponteiro valido
(mesmo caso das 17 de P-67.7/67.10 — normalmente sinal de que a string nunca
deveria ter sido extraida, nao um ponteiro perdido).

Uso: item_equip_ponteiros_filtra.py [--entrada CSV] [--saida CSV]
"""
import sys, csv, argparse
sys.path.insert(0, '.')
from item_equip_extrai import CATEGORIAS, FIM_ULTIMA


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--entrada', default='dados/item_equip_ponteiros.csv')
    ap.add_argument('--saida', default='dados/item_equip_ponteiros_limpo.csv')
    args = ap.parse_args()

    arenas = []
    for i, (jp, cena, en, va_ini) in enumerate(CATEGORIAS):
        va_fim = CATEGORIAS[i + 1][3] if i + 1 < len(CATEGORIAS) else FIM_ULTIMA
        arenas.append((cena, va_ini, va_fim))

    def onde(va):
        return [cena for cena, ini, fim in arenas if ini <= va < fim]

    with open(args.entrada, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    limpas, descartadas = [], []
    ids_com_pelo_menos_uma = set()
    todos_ids = {r['id'] for r in rows}
    for r in rows:
        va = int(r['va_ponteiro'], 16)
        if onde(va):
            limpas.append(r)
            ids_com_pelo_menos_uma.add(r['id'])
        else:
            descartadas.append(r)

    zeradas = sorted(todos_ids - ids_com_pelo_menos_uma)

    with open(args.saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        for r in limpas:
            w.writerow(r)

    print(f'{len(rows)} linhas -> {len(limpas)} ficam, {len(descartadas)} descartadas (fora de toda arena)')
    for r in descartadas:
        print(f'  DESCARTADA: {r["bloco"]} {r["va_ponteiro"]} -> {r["va_string"]} {r["original"][:25]!r} id={r["id"]}')
    print(f'\n{len(zeradas)} strings ficaram com ZERO ponteiro valido apos o filtro:')
    for z in zeradas:
        print(f'  {z}')
    print(f'\n-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

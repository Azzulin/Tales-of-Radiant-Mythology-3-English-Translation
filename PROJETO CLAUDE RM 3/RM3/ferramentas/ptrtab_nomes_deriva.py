#!/usr/bin/env python3
"""Deriva a traducao dos 94 nomes completos de personagem (PTRTAB, P-57) a
partir do glossario ja aprovado (dados/elenco_falantes.csv), em vez de mandar
pro tradutor um nome que ja foi decidido sob outra forma (nome curto).

Uso: ptrtab_nomes_deriva.py <strings_historia.csv> <elenco_falantes.csv> <saida.csv>

Casa cada nome completo (`original`, ex. `クレス・アルベイン`) contra o glossario
por PARTE (separando por nakaguro `・` ou espaco largo `　`) — o glossario guarda
o primeiro nome/apelido curto (`クレス`), nao o nome completo. So' deriva quando
UMA parte bate; nome que nao bate fica com traducao vazia, para tradutor de
verdade decidir (nunca adivinha aqui).
"""
import sys, csv

ARQUIVO = 'v3082_CharGuideTextCName.bin'


def main():
    hist, elc, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    elenco_jp = {}
    for r in csv.DictReader(open(elc, encoding='utf-8')):
        elenco_jp[r['nome_jp']] = r

    nomes = [r for r in csv.DictReader(open(hist, encoding='utf-8'))
             if r['arquivo'] == ARQUIVO]

    linhas = []
    sem_match = []
    for r in nomes:
        full = r['original']
        partes = full.replace('　', '・').split('・')
        achado = next((elenco_jp[p] for p in partes if p in elenco_jp), None)
        if achado:
            linhas.append({
                'id': r['id'], 'original': full, 'traducao': achado['nome_en'],
                'fonte': 'elenco_falantes.csv', 'status': 'revisar',
                'nota': f'derivado do apelido curto `{achado["nome_jp"]}`',
            })
        else:
            linhas.append({
                'id': r['id'], 'original': full, 'traducao': '',
                'fonte': '', 'status': 'pendente',
                'nota': 'sem correspondencia no glossario — nome novo, decidir',
            })
            sem_match.append(full)

    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'{len(linhas)} nomes, {len(linhas)-len(sem_match)} derivados do glossario, '
          f'{len(sem_match)} sem correspondencia -> {saida}')
    if sem_match:
        print('SEM CORRESPONDENCIA (precisam de traducao nova):')
        for n in sem_match:
            print(f'  {n!r}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

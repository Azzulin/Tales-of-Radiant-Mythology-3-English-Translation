#!/usr/bin/env python3
"""Monta o indice de falantes: ator_id -> nome_jp -> nome_en. Ver P-47.

Uso: elenco_index.py <eboot> <elenco_rm3.csv> <preench.psv> <jogos.psv> <saida.csv>

A tabela de elenco vive no EBOOT em 0x08D66EB0, 114 nomes, EUC-JP.
`ator_id` do stream FaceChat e' **1-based** sobre ela: falante = tabela[ator-1].

`jogo_de_origem` NAO vem da ROM: e' conhecimento da serie Tales, marcado como
tal na coluna `fonte_jogo`. Serve para o tradutor casar a voz oficial em ingles.
"""
import sys, csv
import eboot_tabsis as T

VA, N = 0x08D66EB0, 114


def chaves(s):
    """Variantes de chave para casar nome curto do EBOOT com nome completo."""
    out = {s}
    for sep in ('　', '・', ' '):
        if sep in s:
            ps = s.split(sep)
            out.add(ps[0]); out.add(ps[-1])
    return out


def main():
    eb, elc, pre, jog, saida = sys.argv[1:6]
    d = T.ler(eb)
    tabela = {}
    for e in T.entradas(d, VA, N):
        if e['off'] is not None:
            tabela[e['i']] = e['original'].decode('euc_jp')
    assert len(tabela) == N, f'{len(tabela)} nomes, esperado {N}'

    rm3 = list(csv.DictReader(open(elc, encoding='utf-8')))
    por = {}
    for r in rm3:
        for k in chaves(r['nome_jp']):
            por.setdefault(k, r)

    def le_psv(p):
        fh = open(p, encoding='utf-8')
        cab = fh.readline().rstrip('\n').split('|')
        rows = [dict(zip(cab, l.rstrip('\n').split('|')))
                for l in fh if l.strip()]
        fh.close()
        return rows
    preench = {int(r['indice0']): r for r in le_psv(pre)}
    jogos = {r['nome_en_prefixo']: r['jogo_de_origem'] for r in le_psv(jog)}

    linhas = []
    sem_en = []
    for i in range(N):
        nm = tabela[i]
        p = preench.get(i)
        if p:
            en, fonte, jg, papel = p['nome_en'], p['fonte'], p['jogo_de_origem'], p['papel']
        else:
            r = None
            for k in chaves(nm):
                if k in por:
                    r = por[k]; break
            if not r:
                sem_en.append((i, nm)); continue
            en = r['proposta_en']
            fonte = 'rm2' if 'termbase RM2' in r['justificativa'] else 'elenco_rm3'
            jg, papel = '', r['justificativa']
        if not jg:
            jg = jogos.get(en.split()[0], '')
        linhas.append({'ator_id': i + 1, 'indice0': i, 'nome_jp': nm,
                       'nome_en': en, 'fonte_nome': fonte,
                       'jogo_de_origem': jg,
                       'fonte_jogo': 'conhecimento da serie Tales, NAO da ROM' if jg else '',
                       'nota': papel})
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)
    print(f'{len(linhas)} de {N} com nome em ingles -> {saida}')
    if sem_en:
        print(f'SEM NOME EM INGLES ({len(sem_en)}):')
        for i, nm in sem_en:
            print(f'  [{i}] {nm}')
        return 1
    sj = [r for r in linhas if not r['jogo_de_origem']]
    print(f'sem jogo de origem: {len(sj)}' + (' -> ' + ', '.join(r['nome_en'] for r in sj) if sj else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())

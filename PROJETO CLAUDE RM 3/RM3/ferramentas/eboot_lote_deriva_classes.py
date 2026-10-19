#!/usr/bin/env python3
"""Deriva a traducao das 16 descricoes CURTAS de classe a partir da traducao
JA APROVADA das descricoes LONGAS da tela de criacao (P-54). NAO manda para
tradutor: e' a MESMA frase, so' sem o sufixo "(Beginner)"/"(Intermediate)".

Uso: eboot_lote_deriva_classes.py <eboot_dec> <lote_criacao.csv> <saida.csv>

Verifica antes de derivar: a curta tem de ser PREFIXO exato da longa (byte a
byte, ignorando um \\t solto no inicio de uma delas — unico caso conhecido,
classe Hunter). Se algum par nao bater, para e avisa — nao adivinha.
"""
import sys, csv, re
import eboot_tabsis as T

INI_CURTA = 0x08D65B54
N = 16
ID_LONGA_INI = 78   # lote_criacao.csv, ids 78..93


def main():
    eb, criacao_csv, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    d = T.ler(eb)
    ents = T.entradas(d, INI_CURTA, N)

    byid = {int(r['id']): r for r in csv.DictReader(open(criacao_csv, encoding='utf-8'))}

    linhas = []
    prob = []
    for i, e in enumerate(ents):
        jp_curta = e['original'].decode('euc_jp')
        longa = byid.get(ID_LONGA_INI + i)
        if longa is None:
            prob.append(f'{i}: id {ID_LONGA_INI+i} nao existe em {criacao_csv}')
            continue
        jp_longa = longa['original'].replace('\\n', '\n')

        tab_curta = jp_curta.startswith('\t')
        base_curta = jp_curta[1:] if tab_curta else jp_curta
        if not jp_longa.startswith(base_curta):
            prob.append(f'{i}: curta nao e prefixo da longa\n'
                        f'   curta: {jp_curta!r}\n   longa: {jp_longa!r}')
            continue

        en_longa = longa['traducao']
        # remove o sufixo de dificuldade (vem colado no fim, sem \n antes)
        en_curta = re.sub(r'\s*\((Beginner|Intermediate|Intermediate-Advanced)\)\s*$',
                           '', en_longa)
        if en_curta == en_longa and jp_longa != base_curta:
            prob.append(f'{i}: longa tem sufixo em japones mas o padrao nao achou '
                        f'sufixo em ingles: {en_longa!r}')
            continue
        # a curta nao tem \n nenhum (verificado nas 16 — P-54): junta numa linha so'
        en_curta = en_curta.replace('\\n', ' ').strip()
        if tab_curta:
            en_curta = '\t' + en_curta

        linhas.append({
            'idx': i, 'va_ponteiro': f'0x{e["va_ponteiro"]:08X}',
            'original': jp_curta.replace('\t', '\\t'),
            'traducao': en_curta.replace('\t', '\\t'),
            'fonte_id_lote_criacao': ID_LONGA_INI + i,
            'nota': 'derivado de lote_criacao.csv, sufixo de dificuldade removido'
                    + (' — tinha \\t solto no inicio, preservado' if tab_curta else ''),
        })

    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'{len(linhas)} de {N} derivadas -> {saida}')
    if prob:
        print(f'PROBLEMAS ({len(prob)}) — nao derivados, precisam de traducao nova:')
        for p in prob:
            print('  ' + p)
        return 1
    print('todas as 16 derivadas sem ambiguidade')
    return 0


if __name__ == '__main__':
    sys.exit(main())

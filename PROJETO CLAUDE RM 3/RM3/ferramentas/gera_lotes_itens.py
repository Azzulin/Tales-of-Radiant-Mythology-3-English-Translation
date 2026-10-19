#!/usr/bin/env python3
"""Gera os lotes ITEM-NN a partir de item_equip_falantes.tsv. Ver P-67.4/67.7.

Uso: gera_lotes_itens.py <item_equip_falantes.tsv> <dir_saida> [--manifesto ARQ]

Corta por CATEGORIA inteira sempre que possivel (nunca mistura duas categorias
no meio de um lote de forma que fique confuso pro tradutor — cada lote lista
as categorias completas que cobre). Categoria maior que o teto (320 falas,
mesmo de sempre) e' dividida em partes -a/-b/-c dentro dela mesma. Categorias
pequenas se juntam ate' o teto, na ordem em que aparecem no arquivo de
origem (a mesma ordem de `CATEGORIAS` em `item_equip_extrai.py`).

Numeracao sequencial simples (`ITEM-01`, `ITEM-02`...) em vez de nomear o
lote pelas categorias — junta gente demais pra caber no nome. O manifesto e
o `.md` de cada lote dizem quais categorias entram ali.
"""
import sys, csv, os, collections

MAX_FALAS = 320
MIN_FALAS = 60


def main():
    src, dst = sys.argv[1], sys.argv[2]
    manifesto = '00_MANIFESTO_ITENS.csv'
    if '--manifesto' in sys.argv:
        manifesto = sys.argv[sys.argv.index('--manifesto') + 1]
    os.makedirs(dst, exist_ok=True)
    rows = list(csv.DictReader(open(src, encoding='utf-8-sig'), delimiter='\t'))

    porcat = collections.OrderedDict()
    for r in rows:
        porcat.setdefault(r['cena'], []).append(r)

    # --- fatia categoria grande demais em pedacos -a/-b/-c... ---
    fatias = []  # cada item: (nome_categoria, sufixo_ou_None, lista_de_linhas)
    for cat, rs in porcat.items():
        if len(rs) <= MAX_FALAS:
            fatias.append((cat, None, rs))
        else:
            partes = [rs[i:i + MAX_FALAS] for i in range(0, len(rs), MAX_FALAS)]
            sufixos = 'abcdefghijklmnop'
            for i, p in enumerate(partes):
                fatias.append((cat, sufixos[i], p))

    # --- agrupa fatias pequenas ate' o teto, na ordem original ---
    grupos = []
    cur, cur_n = [], 0
    for cat, suf, rs in fatias:
        if cur and cur_n + len(rs) > MAX_FALAS:
            grupos.append(cur)
            cur, cur_n = [], 0
        cur.append((cat, suf, rs))
        cur_n += len(rs)
    if cur:
        grupos.append(cur)
    # funde grupo final minusculo no anterior
    fim = []
    for g in grupos:
        n = sum(len(rs) for _, _, rs in g)
        if fim:
            n_prev = sum(len(rs) for _, _, rs in fim[-1])
            if n < MIN_FALAS and n_prev + n <= MAX_FALAS:
                fim[-1] = fim[-1] + g
                continue
        fim.append(g)
    grupos = fim

    COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor']
    man = []
    for i, g in enumerate(grupos, 1):
        nome = f'ITEM-{i:02d}'
        linhas = [r for _, _, rs in g for r in rs]
        categorias_aqui = [(cat, suf, len(rs)) for cat, suf, rs in g]

        cam = os.path.join(dst, f'{nome}.tsv')
        with open(cam, 'w', encoding='utf-8', newline='') as fh:
            fh.write('\t'.join(COLS) + '\n')
            for r in linhas:
                campos = [r['id'], r['cena'], r['ordem'], r['falante_jp'], r['falante_en'],
                          r['tipo'], r['control_codes'], r['original'], '', '']
                for c in campos:
                    assert '\t' not in c and '\n' not in c, f'campo com TAB/LF em {r["id"]}'
                fh.write('\t'.join(campos) + '\n')

        with open(os.path.join(dst, f'{nome}.md'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(f'# {nome} — briefing\n\n')
            fh.write('| | |\n|---|---|\n')
            fh.write(f'| Falas | **{len(linhas)}** |\n')
            fh.write('| Categorias | ' + ', '.join(
                f'`{cat}`' + (f' (parte {suf})' if suf else '') + f' ({n})'
                for cat, suf, n in categorias_aqui) + ' |\n')

        man.append({
            'lote': nome, 'falas': len(linhas),
            'categorias': ';'.join(f'{cat}{"-" + suf if suf else ""}' for cat, suf, _ in categorias_aqui),
            'status': 'pendente',
        })

    with open(os.path.join(dst, manifesto), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(man[0].keys()))
        w.writeheader()
        for r in man:
            w.writerow(r)

    tot = sum(m['falas'] for m in man)
    assert tot == len(rows), f'{tot} falas nos lotes != {len(rows)} no corpus'
    print(f'{len(man)} lotes, {tot} falas (soma == corpus, nada perdido nem duplicado)')
    print(f'menor lote: {min(m["falas"] for m in man)} falas   '
          f'maior: {max(m["falas"] for m in man)} falas   media: {tot // len(man)}')
    print(f'-> {dst}/')


if __name__ == '__main__':
    main()

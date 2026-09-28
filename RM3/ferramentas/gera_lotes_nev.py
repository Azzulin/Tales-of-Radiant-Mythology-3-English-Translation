#!/usr/bin/env python3
"""Gera os lotes NEV-XX a partir de nev_falantes.csv. Ver P-64.

Uso: gera_lotes_nev.py <nev_falantes.csv> <dir_saida> [--manifesto 00_MANIFESTO_NEV.csv]

`gera_lotes.py` corta por CAPITULO (`<prefixo>NN_`) porque mev/cev/qev/tev tem
essa estrutura. `nev` nao tem: as 88 cenas sao `nev01_NNN.scr` — um so'
"capitulo" (01) do inicio ao fim, cada cena um vinheta independente (media
~20 falas). Cortar por capitulo daria 1 lote so' de 1.767 falas (ou 2, se
dividido ao meio — ainda 800+ cada, muito acima do teto de sempre).

Em vez disso, corta por **grupo de cenas consecutivas**, mesmo teto de sempre
(MAX_FALAS=320, MIN_FALAS=60, ver `gera_lotes.py`): acumula cena a cena ate'
passar de 320 falas, fecha o lote, comeca o proximo; lote final abaixo de 60
funde no anterior. Nunca quebra uma cena ao meio entre dois lotes.

Mesma saida de sempre por lote: `<LOTE>.tsv` + `<LOTE>.md`, e um manifesto no
diretorio. Falante sai fixo como `(NPC da guilda)` — ver docstring de
`nev_falas_extrai.py` e P-64 para o porque (o comando de exibicao de `nev` nao
carrega ID de ator, ao contrario do 0x006B usado nas outras frentes).
"""
import sys, csv, os, re, collections

MAX_FALAS = 320
MIN_FALAS = 60


def main():
    src, dst = sys.argv[1], sys.argv[2]
    manifesto = '00_MANIFESTO_NEV.csv'
    if '--manifesto' in sys.argv:
        manifesto = sys.argv[sys.argv.index('--manifesto') + 1]
    os.makedirs(dst, exist_ok=True)
    rows = list(csv.DictReader(open(src, encoding='utf-8')))

    porcena = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r['cena'], int(r['ordem']))):
        porcena.setdefault(r['cena'], []).append(r)

    # --- agrupa cena a cena ate' passar do teto ---
    grupos = []
    cur_cenas, cur_n = [], 0
    for cena, rs in porcena.items():
        if cur_cenas and cur_n + len(rs) > MAX_FALAS:
            grupos.append(cur_cenas)
            cur_cenas, cur_n = [], 0
        cur_cenas.append(cena)
        cur_n += len(rs)
    if cur_cenas:
        grupos.append(cur_cenas)
    # funde grupo final minusculo no anterior, mesmo teto de MAX_FALAS
    fim = []
    for g in grupos:
        n = sum(len(porcena[c]) for c in g)
        if fim:
            n_prev = sum(len(porcena[c]) for c in fim[-1])
            if n < MIN_FALAS and n_prev + n <= MAX_FALAS:
                fim[-1] = fim[-1] + g
                continue
        fim.append(g)
    grupos = fim

    def nome_lote(cenas):
        primeiro = re.match(r'nev01_(\d+)', cenas[0]).group(1)
        ultimo = re.match(r'nev01_(\d+)', cenas[-1]).group(1)
        return f'NEV-{primeiro}' if primeiro == ultimo else f'NEV-{primeiro}_{ultimo}'

    COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor']
    man = []
    for cenas in grupos:
        rs = [r for c in cenas for r in porcena[c]]
        nome = nome_lote(cenas)
        props = collections.Counter()
        for r in rs:
            for m in re.findall(r'[ァ-ヶ][ァ-ヶー・]{2,}', r['original']):
                props[m] += 1

        cam = os.path.join(dst, f'{nome}.tsv')
        with open(cam, 'w', encoding='utf-8', newline='') as fh:
            fh.write('\t'.join(COLS) + '\n')
            for r in rs:
                campos = [r['id'], r['cena'], r['ordem'], r['falante'], r['falante'],
                          r['tipo'], r['control_codes'], r['original'], '', '']
                for c in campos:
                    assert '\t' not in c and '\n' not in c, f'campo com TAB/LF em {r["id"]}'
                fh.write('\t'.join(campos) + '\n')

        with open(os.path.join(dst, f'{nome}.md'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(f'# {nome} — briefing\n\n')
            fh.write('| | |\n|---|---|\n')
            fh.write(f'| Falas | **{len(rs)}** |\n| Cenas | {len(cenas)} |\n')
            fh.write(f'| Bytes de japones | {sum(int(r["bytes_jp"]) for r in rs):,} |\n')
            fh.write(f'| Primeira cena | `{cenas[0]}` |\n| Ultima cena | `{cenas[-1]}` |\n\n')
            top = [f'`{k}` ({v}x)' for k, v in props.most_common(18)]
            if top:
                fh.write('## Nomes proprios em katakana mais frequentes\n\n')
                fh.write('Confira cada um no `INDICE_NOMES.md`. Se nao estiver la, **pare e '
                         'pergunte** em vez de inventar grafia.\n\n')
                fh.write(', '.join(top) + '\n\n')
            fh.write('## Cenas, na ordem\n\n')
            fh.write(', '.join(f'`{c}`' for c in cenas) + '\n')

        man.append({'lote': nome, 'falas': len(rs), 'cenas': len(cenas),
                    'bytes_jp': sum(int(r['bytes_jp']) for r in rs),
                    'falantes': 1, 'primeira_cena': cenas[0], 'ultima_cena': cenas[-1],
                    'personagem': sum(1 for r in rs if r['tipo'] == 'personagem'),
                    'narracao': 0, 'escolha': 0, 'sistema': 0, 'sem_caixa': 0,
                    'status': 'pendente'})

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

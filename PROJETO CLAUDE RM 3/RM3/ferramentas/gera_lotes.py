#!/usr/bin/env python3
"""Gera os lotes de traducao de uma frente de dialogo FaceChat. Ver P-48.

Uso: gera_lotes.py <falantes.csv> <elenco_falantes.csv> <dir_saida>
                    [--prefixo cev] [--rotulo CEV] [--manifesto 00_MANIFESTO_CEV.csv]

Sem as flags, o comportamento e' exatamente o da historia principal (`mev`,
lotes `MEV-XX`, `00_MANIFESTO.csv`) — nenhuma chamada existente muda. As flags
existem para reusar o mesmo gerador noutra frente de mesma forma (ex.: skits,
`cev`) sem duplicar a logica nem arriscar sobrescrever o manifesto da frente
anterior.

Por lote emite:
  <LOTE>.tsv  — o corpus, uma fala por linha, coluna `traducao` vazia
  <LOTE>.md   — briefing: capitulo, cenas, elenco presente, nomes proprios novos

E, no diretorio: `<manifesto>` com o resumo de cada lote.

O TSV usa TAB como separador e **nenhum campo contem TAB**; a quebra de linha
dentro da fala e' a sequencia literal `\\n` (o CRLF real do FaceChat, ver P-21).
"""
import sys, csv, os, re, collections

MAX_FALAS = 320          # acima disso o capitulo e' dividido
MIN_FALAS = 60           # abaixo disso e' juntado ao anterior


def capitulo(cena, prefixo):
    m = re.match(prefixo + r'(\d\d)_', cena)
    return m.group(1) if m else '??'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src, elc, dst = args[0], args[1], args[2]
    prefixo = 'mev'
    rotulo = 'MEV'
    manifesto = '00_MANIFESTO.csv'
    if '--prefixo' in sys.argv:
        prefixo = sys.argv[sys.argv.index('--prefixo') + 1]
    if '--rotulo' in sys.argv:
        rotulo = sys.argv[sys.argv.index('--rotulo') + 1]
    if '--manifesto' in sys.argv:
        manifesto = sys.argv[sys.argv.index('--manifesto') + 1]
    os.makedirs(dst, exist_ok=True)
    rows = list(csv.DictReader(open(src, encoding='utf-8')))
    elenco = {r['nome_jp']: r for r in csv.DictReader(open(elc, encoding='utf-8'))}

    # --- agrupa por capitulo, preservando a ordem de cena e de fala ---
    porcap = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r['cena'], int(r['ordem']))):
        porcap.setdefault(capitulo(r['cena'], prefixo), []).append(r)

    # --- corta em lotes ---
    lotes = []
    for cap, rs in porcap.items():
        if len(rs) > MAX_FALAS:
            cenas = sorted({r['cena'] for r in rs})
            meio = len(cenas) // 2
            a = {c for c in cenas[:meio]}
            lotes.append((f'{rotulo}-{cap}a', [r for r in rs if r['cena'] in a]))
            lotes.append((f'{rotulo}-{cap}b', [r for r in rs if r['cena'] not in a]))
        else:
            lotes.append((f'{rotulo}-{cap}', rs))
    # junta lote minusculo ao anterior — mas nao deixa a cadeia de fusao passar
    # de MAX_FALAS. Sem este teto, uma sequencia de varios grupos minusculos
    # seguidos (comum em frentes de grupos pequenos, como skits) se funde toda
    # junta num lote so', gigante e sem nome pratico — o teste so' olhava o
    # tamanho do grupo ENTRANDO, nunca o tamanho acumulado do lote resultante.
    fim = []
    for nome, rs in lotes:
        if fim and len(rs) < MIN_FALAS and len(fim[-1][1]) + len(rs) <= MAX_FALAS:
            pn, prs = fim[-1]
            fim[-1] = (f'{pn}+{nome.split("-")[1]}', prs + rs)
        else:
            fim.append((nome, rs))
    lotes = fim

    COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor']
    man = []
    vistos_falantes = set()
    for nome, rs in lotes:
        cenas = sorted({r['cena'] for r in rs})
        # elenco presente, por volume de fala
        cont = collections.Counter(r['falante'] for r in rs)
        # nomes proprios em katakana com 3+ caracteres, para o briefing
        props = collections.Counter()
        for r in rs:
            for m in re.findall(r'[ァ-ヶ][ァ-ヶー・]{2,}', r['original']):
                props[m] += 1

        cam = os.path.join(dst, f'{nome}.tsv')
        with open(cam, 'w', encoding='utf-8', newline='') as fh:
            fh.write('\t'.join(COLS) + '\n')
            for r in rs:
                e = elenco.get(r['falante'])
                fen = e['nome_en'] if e else r['falante']
                campos = [r['id'], r['cena'], r['ordem'], r['falante'], fen,
                          r['tipo'], r['control_codes'], r['original'], '', '']
                for c in campos:
                    assert '\t' not in c and '\n' not in c, f'campo com TAB/LF em {r["id"]}'
                fh.write('\t'.join(campos) + '\n')

        novos = [f for f in cont if f not in vistos_falantes and f in elenco]
        vistos_falantes |= set(cont)
        with open(os.path.join(dst, f'{nome}.md'), 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(f'# {nome} — briefing\n\n')
            fh.write(f'| | |\n|---|---|\n')
            fh.write(f'| Falas | **{len(rs)}** |\n| Cenas | {len(cenas)} |\n')
            fh.write(f'| Bytes de japones | {sum(int(r["bytes_jp"]) for r in rs):,} |\n')
            fh.write(f'| Primeira cena | `{cenas[0]}` |\n| Ultima cena | `{cenas[-1]}` |\n\n')
            fh.write('## Elenco presente, por volume de fala\n\n')
            fh.write('| Falante (jp) | Nome adotado | Jogo de origem | Falas |\n|---|---|---|---|\n')
            for f, n in cont.most_common():
                e = elenco.get(f)
                fh.write(f'| `{f}` | **{e["nome_en"] if e else f}** | '
                         f'{e["jogo_de_origem"] if e else "—"} | {n} |\n')
            if novos:
                fh.write('\n## Estreiam neste lote\n\n')
                fh.write('Primeira aparicao na historia principal — a voz que voce escolher aqui '
                         'governa todos os lotes seguintes.\n\n')
                for f in novos:
                    e = elenco[f]
                    fh.write(f'- **{e["nome_en"]}** (`{f}`) — {e["jogo_de_origem"]}\n')
            top = [f'`{k}` ({v}x)' for k, v in props.most_common(18)]
            if top:
                fh.write('\n## Nomes proprios em katakana mais frequentes\n\n')
                fh.write('Confira cada um no `INDICE_NOMES.md`. Se nao estiver la, **pare e '
                         'pergunte** em vez de inventar grafia.\n\n')
                fh.write(', '.join(top) + '\n')
            fh.write('\n## Cenas, na ordem\n\n')
            fh.write(', '.join(f'`{c}`' for c in cenas) + '\n')

        man.append({'lote': nome, 'falas': len(rs), 'cenas': len(cenas),
                    'bytes_jp': sum(int(r['bytes_jp']) for r in rs),
                    'falantes': len(cont), 'primeira_cena': cenas[0],
                    'ultima_cena': cenas[-1],
                    'personagem': sum(1 for r in rs if r['tipo'] == 'personagem'),
                    'narracao': sum(1 for r in rs if r['tipo'] == 'narracao'),
                    'escolha': sum(1 for r in rs if r['tipo'] == 'escolha'),
                    'sistema': sum(1 for r in rs if r['tipo'] == 'sistema'),
                    'sem_caixa': sum(1 for r in rs if r['tipo'] == 'sem_caixa'),
                    'status': 'pendente'})
    with open(os.path.join(dst, manifesto), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(man[0].keys()))
        w.writeheader()
        for r in man:
            w.writerow(r)

    tot = sum(m['falas'] for m in man)
    assert tot == len(rows), f'{tot} falas nos lotes != {len(rows)} no corpus'
    print(f'{len(man)} lotes, {tot} falas (soma == corpus, nada perdido nem duplicado)')
    print(f'{sum(m["bytes_jp"] for m in man):,} bytes de japones')
    print(f'menor lote: {min(m["falas"] for m in man)} falas   '
          f'maior: {max(m["falas"] for m in man)} falas   '
          f'media: {tot//len(man)}')
    print(f'-> {dst}/')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Gera o pacote de lotes de traducao TXZ-XX a partir de dados/strings_txz.csv.

Frente `.txz` = texto de quest sem falante (objetivo/descricao/recompensa, quadro
de missao). Formato-fonte documentado em `ferramentas/txz.py`: Shift-JIS, **folga
zero de byte** por string (offset fixo dentro do container, sem ponteiro
reponteavel). Por isso o lote carrega uma coluna extra que nenhum outro lote tem:
`orcamento_bytes` — o teto exato, em bytes Shift-JIS, que a `traducao` daquela
linha nao pode passar.

Uso (rodar de dentro de RM3/ferramentas/, import nao e' relativo mas o caminho
default assume esse cwd):

    py txz_lote_gera.py
    py txz_lote_gera.py --csv ../dados/strings_txz.csv --saida ../lotes --cap 300

Nao traduz nada — `traducao` sai vazia em todo lote gerado. So' organiza.
"""
import argparse
import csv
import os
from collections import OrderedDict, Counter

NL = '\\n'  # sequencia literal de 2 caracteres usada no .tsv para quebra de linha
            # (ver P-17/P-19 em PADROES_DESCOBERTOS.md); nao e' um \n real.

COLUNAS_LOTE = ('id', 'arquivo', 'original', 'traducao', 'nota_do_tradutor',
                'orcamento_bytes')


def le_csv(caminho):
    with open(caminho, encoding='utf-8-sig', newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError(f'{caminho}: nenhuma linha lida')
    faltando = set(('id', 'arquivo', 'original', 'bytes_max')) - set(rows[0].keys())
    if faltando:
        raise ValueError(f'{caminho}: colunas ausentes {sorted(faltando)}')
    return rows


def agrupa_por_arquivo(rows):
    """Preserva a ordem de aparicao no CSV; um `arquivo` vira um bloco continuo."""
    grupos = OrderedDict()
    for r in rows:
        grupos.setdefault(r['arquivo'], []).append(r)
    return grupos


def corta_em_lotes(grupos, cap):
    """Empacota blocos de arquivo inteiros em lotes de ate `cap` linhas, na ordem
    em que os arquivos aparecem. Nunca parte um arquivo no meio (o pedido explicito
    e' 'cortar por arquivo de origem quando possivel'); se um unico arquivo for
    maior que `cap`, ele vira um lote sozinho (maior que o teto, mas inteiro).
    """
    lotes = []
    atual = []
    atual_n = 0
    for arquivo, linhas in grupos.items():
        if atual_n > 0 and atual_n + len(linhas) > cap:
            lotes.append(atual)
            atual, atual_n = [], 0
        atual.extend(linhas)
        atual_n += len(linhas)
    if atual:
        lotes.append(atual)
    return lotes


def orcamento(original):
    return len(original.encode('shift_jis'))


def extrai_placeholders(original):
    """So' para o briefing .md: lista os marcadores <...> e tags [...] presentes,
    e conta o marcador de nome do jogador OO, se aparecer nesta frente."""
    import re
    ph = re.findall('＜[^＞]*＞', original)
    tags = re.findall(r'\[[^\]]*\]', original)
    return ph, tags


def escreve_tsv(caminho, linhas):
    with open(caminho, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\t'.join(COLUNAS_LOTE) + '\n')
        for r in linhas:
            original = r['original']
            row = [
                r['id'],
                r['arquivo'],
                original,
                '',  # traducao
                '',  # nota_do_tradutor
                str(orcamento(original)),
            ]
            for campo in row:
                if '\t' in campo or '\n' in campo or '\r' in campo:
                    raise ValueError(f'campo com TAB/CR/LF literal, quebraria o TSV: {campo!r}')
            fh.write('\t'.join(row) + '\n')


def escreve_md(caminho, nome_lote, linhas):
    total = len(linhas)
    bytes_jp = sum(orcamento(r['original']) for r in linhas)
    arquivos = list(OrderedDict.fromkeys(r['arquivo'] for r in linhas))
    bmin = min(orcamento(r['original']) for r in linhas)
    bmax = max(orcamento(r['original']) for r in linhas)
    bmedia = bytes_jp / total if total else 0

    todos_ph = Counter()
    todas_tags = Counter()
    marca_nome = 0
    for r in linhas:
        ph, tags = extrai_placeholders(r['original'])
        todos_ph.update(ph)
        todas_tags.update(tags)
        marca_nome += r['original'].count('○○')

    # linhas com orcamento incomum (fora da faixa tipica do lote) — heads-up para
    # o tradutor, nao e' erro de extracao, e' dado real do jogo (ver 00_LEIA_PRIMEIRO_TXZ.md)
    outliers = sorted(linhas, key=lambda r: -orcamento(r['original']))[:3]

    with open(caminho, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(f'# {nome_lote} — briefing\n\n')
        fh.write('| | |\n|---|---|\n')
        fh.write(f'| Linhas | **{total}** |\n')
        fh.write(f'| Arquivos `.txz` | {len(arquivos)} |\n')
        fh.write(f'| Bytes de japones (soma dos orcamentos) | {bytes_jp:,} |\n')
        fh.write(f'| Orcamento por linha (min / media / max) | {bmin} / {bmedia:.0f} / {bmax} |\n')
        fh.write('\n## Arquivos cobertos, na ordem\n\n')
        for a in arquivos:
            n = sum(1 for r in linhas if r['arquivo'] == a)
            fh.write(f'- `{a}` — {n} linhas\n')

        fh.write('\n## Marcadores de controle presentes neste lote\n\n')
        fh.write('Sao os equivalentes desta frente ao `%s`/`%d`/`\\\\n` do pacote principal — R2 '
                  '(control codes intocaveis) vale aqui do mesmo jeito, so\' que com tokens '
                  'diferentes. Reproduza cada um **na mesma quantidade e com o mesmo texto '
                  'japones dentro dos colchetes** (nao traduza o que esta dentro de `[...]`), '
                  'e cada `<...>` exatamente como esta.\n\n')
        if todos_ph:
            fh.write('**Marcadores `<...>` (substituidos em tempo de execucao por nome de item, '
                      'de masmorra, numero, etc.):**\n\n')
            for tok, n in todos_ph.most_common():
                fh.write(f'- `{tok}` — {n}x\n')
        else:
            fh.write('Nenhum marcador `<...>` neste lote.\n')
        fh.write('\n')
        if todas_tags:
            fh.write('**Tags de cor `[...]`:**\n\n')
            for tok, n in todas_tags.most_common():
                fh.write(f'- `{tok}` — {n}x\n')
        else:
            fh.write('Nenhuma tag `[...]` neste lote.\n')
        if marca_nome:
            fh.write(f'\n**Marcador de nome do jogador OO:** aparece {marca_nome}x neste lote — '
                      'mesma regra do pacote principal (R2): reproduza exatamente, nao remova.\n')

        fh.write('\n## Linhas de orcamento fora da curva (nao e\' erro de extracao)\n\n')
        fh.write('Estas poucas linhas tem um `original` muito maior que a media do lote (texto '
                  'repetido/concatenado que veio assim do proprio arquivo do jogo). Traduza o '
                  'conteudo real e **anote em `nota_do_tradutor`** se algo parecer degenerado ou '
                  'redundante demais para fazer sentido como fala — nao tente "consertar" '
                  'reduzindo o texto por conta propria alem do que o orcamento pedir.\n\n')
        for r in outliers:
            trecho = r['original'][:60].replace('\t', ' ')
            fh.write(f'- `{r["id"]}` — orcamento {orcamento(r["original"])} bytes: `{trecho}...`\n')

        fh.write('\n## Como este lote e\' aceito\n\n')
        fh.write('```\n')
        fh.write(f'py valida_retorno_txz.py ../lotes/{nome_lote}.tsv ../lotes/{nome_lote}_retorno.tsv\n')
        fh.write('```\n\n')
        fh.write('Ver `00_LEIA_PRIMEIRO_TXZ.md` para o mecanismo de orcamento de bytes e '
                  'exemplos reais de como ele muda a estrategia de traducao.\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--csv', default='../dados/strings_txz.csv')
    ap.add_argument('--saida', default='../lotes')
    ap.add_argument('--cap', type=int, default=300,
                     help='teto de linhas por lote (padrao 300, mesma faixa dos outros pacotes)')
    ap.add_argument('--rotulo', default='TXZ')
    ap.add_argument('--manifesto', default='00_MANIFESTO_TXZ.csv')
    args = ap.parse_args()

    rows = le_csv(args.csv)

    # confere que o orcamento recalculado bate com o bytes_max ja' dumpado — se
    # nao bater, a fonte mudou de formato e este script nao deve seguir calado.
    divergentes = [r for r in rows if orcamento(r['original']) != int(r['bytes_max'])]
    if divergentes:
        raise SystemExit(
            f'{len(divergentes)} linha(s) onde bytes_max do CSV nao bate com o recalculo '
            f'Shift-JIS do `original` — pare e confira dados/strings_txz.csv antes de gerar '
            f'lotes (primeira: {divergentes[0]["id"]})')

    grupos = agrupa_por_arquivo(rows)
    lotes = corta_em_lotes(grupos, args.cap)

    os.makedirs(args.saida, exist_ok=True)
    manifesto_linhas = []
    for i, linhas in enumerate(lotes, 1):
        nome_lote = f'{args.rotulo}-{i:02d}'
        tsv_path = os.path.join(args.saida, f'{nome_lote}.tsv')
        md_path = os.path.join(args.saida, f'{nome_lote}.md')
        escreve_tsv(tsv_path, linhas)
        escreve_md(md_path, nome_lote, linhas)

        arquivos = list(OrderedDict.fromkeys(r['arquivo'] for r in linhas))
        manifesto_linhas.append({
            'lote': nome_lote,
            'linhas': len(linhas),
            'arquivos': len(arquivos),
            'bytes_jp': sum(orcamento(r['original']) for r in linhas),
            'primeiro_arquivo': arquivos[0],
            'ultimo_arquivo': arquivos[-1],
            'status': 'pendente',
        })
        print(f'{nome_lote}: {len(linhas)} linhas, {len(arquivos)} arquivo(s) -> {tsv_path}')

    manifesto_path = os.path.join(args.saida, args.manifesto)
    with open(manifesto_path, 'w', encoding='utf-8', newline='\n') as fh:
        campos = ['lote', 'linhas', 'arquivos', 'bytes_jp', 'primeiro_arquivo',
                  'ultimo_arquivo', 'status']
        w = csv.DictWriter(fh, fieldnames=campos, lineterminator='\n')
        w.writeheader()
        for r in manifesto_linhas:
            w.writerow(r)
    print(f'manifesto: {manifesto_path}')
    print(f'total: {len(rows)} linhas em {len(lotes)} lote(s)')


if __name__ == '__main__':
    main()

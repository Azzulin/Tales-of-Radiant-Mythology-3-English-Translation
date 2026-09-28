#!/usr/bin/env python3
"""Deriva o texto da CAIXA DE NOME (P-63.2) a partir de `dados/elenco_falantes.csv`.

Uso: elenco_nomebox_deriva.py <saida.csv>

`elenco_falantes.csv` guarda o nome COMPLETO (Nome Sobrenome, ex. "Kanonno
Grassvalley") — usado ate agora so' como referencia para achar quem fala cada
linha, e como fonte de `ficha_nomes.csv`/PTRTAB (P-57). A caixa de nome do
jogo tem uma arena de so' 1.203 B para as 114 entradas (P-63.2); os 114 nomes
completos somam 1.338 B e estouram em 135 B.

Regra: primeiro nome (a serie Tales localizada NUNCA mostra sobrenome na
caixa de dialogo — "Cress", nao "Cress Albane" — mesmo quando o jogo tem
varios personagens historicamente com o mesmo primeiro nome, como as quatro
Kanonno; isso e' fiel ao jogo, nao colisao a resolver). Exceção: entradas que
NAO sao nome de pessoa, e sim titulo/papel generico com sufixo numerico ou de
letra (`Reserve 1`, `Henchman A`, `Dawn Cultist 1`...) — cortar no primeiro
espaço nelas produziria uma palavra que parece nome proprio mas nao é
("Dawn" sozinho, por exemplo). Para essas, mantem o substantivo inteiro e
corta so' o sufixo de desambiguação (ou mantém tudo, se já é curto).
"""
import sys, csv

# indice0 -> texto da caixa de nome, quando a regra generica (primeiro token)
# produziria algo enganoso. Todo o resto usa `nome_en.split(' ')[0]`.
EXCECOES = {
    86: 'Original Kanonno',   # nao "Original" sozinho
    103: 'Young Man',         # nao "Young" sozinho
    105: 'Dawn Cultist',      # nao "Dawn" sozinho (4 entradas, mesmo texto)
    106: 'Dawn Cultist',
    107: 'Dawn Cultist',
    108: 'Dawn Cultist',
    109: 'Wanted Criminal',   # nao "Wanted" sozinho
}


def main():
    saida = sys.argv[1]
    rows = list(csv.DictReader(open('../dados/elenco_falantes.csv', encoding='utf-8-sig')))
    out = []
    for r in rows:
        i = int(r['indice0'])
        curto = EXCECOES.get(i, r['nome_en'].split(' ')[0].rstrip(','))
        out.append({
            'id': f'elenco#{i}', 'original': r['nome_jp'], 'traducao': curto,
            'fonte': 'elenco_falantes.csv (primeiro nome)' if i not in EXCECOES
                     else 'elenco_falantes.csv (excecao — titulo generico)',
            'status': 'revisar', 'nota': '',
        })
    with open(saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['id', 'original', 'traducao', 'fonte', 'status', 'nota'])
        w.writeheader()
        for r in out:
            w.writerow(r)
    total = len({r['traducao'] for r in out})
    bytes_ = sum(len(s.encode('ascii')) + 1 for s in {r['traducao'] for r in out})
    print(f'{len(out)} entradas, {total} distintas, {bytes_} B (arena disponivel: 1203 B)')


if __name__ == '__main__':
    main()

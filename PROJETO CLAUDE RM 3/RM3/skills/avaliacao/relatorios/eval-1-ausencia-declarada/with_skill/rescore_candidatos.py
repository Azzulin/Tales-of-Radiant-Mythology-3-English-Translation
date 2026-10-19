#!/usr/bin/env python3
"""Segunda passada de inspecao ocular sobre os candidatos que varre_cinco_ext.py
gravou em <prefixo>_candidatos.csv.

Por que existe: o filtro "kana obrigatorio" da skill acha candidato, mas nao prova
que uma frente esta limpa nem que um candidato e' texto de verdade (secao 3 da
skill). Confusao de dado binario com kana em VOLUME (floats/animacao/malha) e o
modo de falha esperado, entao esta passada:

  1. Reordena os distintos de cada balde kana por "densidade de kana" (proporcao
     de caracteres kana + quantidade de kana distintos + comprimento) para trazer
     o que mais parece frase para o topo -- e' ali que uma frase real aparece.
  2. Reordena tambem por COMPRIMENTO (uma frase real tende a ser mais longa que
     um par de bytes que por acaso caiu em kana valido).
  3. Para o balde kanji (sem kana por definicao -- ja e' 'tecnica' pela propria
     regra da skill), so' amostra por frequencia/comprimento para confirmar que
     e' ruido estrutural (padrao binario repetido), nao para promover a texto.

Nao abre a ISO. So' le o CSV de candidatos que a varredura ja gravou.

Uso: rescore_candidatos.py <prefixo>_candidatos.csv
"""
import csv, sys, collections, re

KANA = re.compile(r'[ぁ-んァ-ヶｦ-ﾟー]')


def score(t):
    kana_chars = KANA.findall(t)
    if not kana_chars:
        return -1
    ratio = len(kana_chars) / len(t)
    distinct_kana = len(set(kana_chars))
    return ratio * 10 + distinct_kana + len(t) * 0.05


def main():
    path = sys.argv[1]
    rows = collections.defaultdict(list)
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows[(r['ext'], r['classe'])].append(r['texto'])

    for (ext, cl), vals in sorted(rows.items()):
        distinct = collections.Counter(vals)
        print(f"=== {ext}/{cl}: {len(vals)} ocorrencias, {len(distinct)} distintas ===")
        print("-- por densidade de kana (topo = mais parece frase) --")
        for t, n in sorted(distinct.items(), key=lambda kv: -score(kv[0]))[:15]:
            print(f"  s={score(t):5.2f} n={n:<4} len={len(t):<3} {t!r}")
        print("-- por comprimento (frase real tende a ser mais longa) --")
        for t, n in sorted(distinct.items(), key=lambda kv: -len(kv[0]))[:15]:
            print(f"  n={n:<4} len={len(t):<3} {t!r}")
        print()


if __name__ == '__main__':
    main()

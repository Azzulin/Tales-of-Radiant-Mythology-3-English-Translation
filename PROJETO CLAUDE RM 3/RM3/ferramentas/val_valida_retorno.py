#!/usr/bin/env python3
"""Valida os `VAL-NN_out.json` devolvidos pelo agente externo (P-67.12/67.13).

Cinco checagens mecanicas, nessa ordem. Reprovando qualquer uma, o lote volta:

  1. ASCII puro — o EBOOT nao tem como mostrar outra coisa.
  2. Todo `id` existe no lote de origem, e o texto realmente encurtou.
  3. Soma dos bytes cortados >= meta do lote.
  4. Nenhuma descricao decapitada: nada termina em preposicao/artigo/conjuncao,
     e toda descricao acaba em `.`, `!` ou `?`.
  5. Todo nome proprio do `en` de entrada continua na saida.

As checagens 4 e 5 sao o que o passe mecanico de 22/09 nao tinha, e por isso
decepou 68 descricoes de `g1_head` cabendo no orcamento (P-67.13). Tamanho nao
e' criterio de qualidade — perda de sentido e'.

Uso:
  val_valida_retorno.py <VAL-NN.json> <VAL-NN_out.json> [...]
  val_valida_retorno.py --todos dados/item_equip_shrink
"""
import sys, json, os, re, glob, argparse

CAUDA = {
    'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with', 'from',
    'and', 'or', 'but', 'that', 'which', 'who', 'whose', 'as', 'is', 'are',
    'was', 'were', 'be', 'been', 'its', "it's", 'this', 'these', 'those',
    'into', 'onto', 'over', 'under', 'than', 'then', 'when', 'while', 'has',
    'have', 'had', 'can', 'will', 'said', 'made', 'used', 'very', 'more',
    'most', 'such', 'so', 'it', 'his', 'her', 'their', 'one', 'also', 'both',
}
# maiusculas de inicio de frase nao contam como nome proprio
COMUM = {w.capitalize() for w in CAUDA} | {
    'Weapon', 'Recipe', 'Arte', 'Arcane', 'Secret', 'Mystic', 'Spell', 'Can',
    'Contains', 'Commonly', 'Restores', 'Revives', 'Cures', 'Holds', 'Seals',
}


def nomes_proprios(t):
    return {w for w in re.findall(r'\b[A-Z][A-Za-z]{1,}\b', t) if w not in COMUM}


def valida(entrada, saida):
    d = json.load(open(entrada, encoding='utf-8'))
    out = json.load(open(saida, encoding='utf-8'))
    orig = {x['id']: x for x in d['itens']}
    lote = d.get('lote', os.path.basename(entrada))
    meta = d['meta_bytes_a_cortar']

    erros = []
    cortado = 0
    for k, novo in out.items():
        x = orig.get(k)
        if x is None:
            erros.append((k, 'id nao existe no lote de origem'))
            continue
        try:
            b = novo.encode('ascii')
        except UnicodeEncodeError as e:
            erros.append((k, f'nao e ASCII: {e.object[e.start:e.end]!r}'))
            continue
        velho = x['en']
        if len(b) >= len(velho.encode('ascii', 'replace')):
            erros.append((k, 'nao encurtou'))
            continue
        cortado += len(velho.encode('ascii', 'replace')) - len(b)

        if len(velho) > 35:                       # descricao, nao nome de item
            if novo.rstrip()[-1:] not in '.!?':
                erros.append((k, f'nao termina em pontuacao: ...{novo[-28:]!r}'))
            pal = re.findall(r"[A-Za-z']+", novo)
            if pal and pal[-1].lower() in CAUDA:
                erros.append((k, f'frase decapitada: ...{novo[-34:]!r}'))
        perdidos = nomes_proprios(velho) - nomes_proprios(novo)
        if perdidos:
            erros.append((k, f'nome proprio sumiu: {", ".join(sorted(perdidos))}'))
        # P-74: reescrever o comeco de uma frase JA reescrita duplica o rotulo.
        # Nenhum dos dois quebra ASCII nem estoura byte — so' leitura pega.
        m = re.match(r'^([A-Z][a-z]+(?: [a-z]+)?:)\s*\1', novo)
        if m:
            erros.append((k, f'rotulo duplicado: {novo[:34]!r}'))
        m = re.search(r'\b(\w+)\s+\1\b', novo)
        if m and m.group(1).lower() not in ('that', 'had'):
            erros.append((k, f'palavra repetida: {m.group(0)!r}'))

    faltou = meta - cortado
    print(f'\n=== {lote}: {len(out)} itens devolvidos de {len(orig)} ===')
    print(f'  cortado {cortado} B / meta {meta} B  '
          f'{"OK" if faltou <= 0 else f"FALTAM {faltou} B"}')
    print(f'  problemas: {len(erros)}')
    for k, m in erros[:15]:
        print(f'    [{k}] {m}')
    if len(erros) > 15:
        print(f'    ... e mais {len(erros)-15}')

    ok = not erros and faltou <= 0
    print(f'  -> {"ACEITO" if ok else "RECUSADO"}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivos', nargs='*')
    ap.add_argument('--todos', metavar='DIR')
    args = ap.parse_args()

    pares = []
    if args.todos:
        for e in sorted(glob.glob(os.path.join(args.todos, 'VAL-*.json'))):
            if e.endswith('_out.json'):
                continue
            s = e.replace('.json', '_out.json')
            if os.path.exists(s):
                pares.append((e, s))
            else:
                print(f'(ainda sem retorno: {os.path.basename(s)})')
    else:
        pares = list(zip(args.arquivos[::2], args.arquivos[1::2]))

    if not pares:
        print('nada a validar')
        return 0
    todos_ok = all(valida(e, s) for e, s in pares)
    print(f'\n{"TODOS ACEITOS" if todos_ok else "HA LOTE RECUSADO"}')
    return 0 if todos_ok else 1


if __name__ == '__main__':
    sys.exit(main())

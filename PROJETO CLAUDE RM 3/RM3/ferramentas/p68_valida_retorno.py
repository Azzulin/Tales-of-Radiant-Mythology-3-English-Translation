#!/usr/bin/env python3
"""Valida os `*_retorno.tsv` dos lotes P-68 (texto de EBOOT com `max_bytes`).

Cinco checagens. Reprovando qualquer uma, o lote volta inteiro:

  1. ASCII puro — o EBOOT nao tem como mostrar outra coisa.
  2. Toda linha respeitada: `len(traducao) <= max_bytes`, e a soma do bloco
     dentro do espaco real (a soma e' o que decide, a linha isolada so' avisa).
  3. Nenhuma descricao decapitada: nada termina em preposicao/artigo/conjuncao,
     e o que for frase acaba em `.`, `!` ou `?`.
  4. Colunas de endereco e orcamento intactas (`va_ponteiros`, `bytes_jp`,
     `max_bytes`) — se mudarem, o lote nao entra no build.
  5. Nada em branco, e nada com japones sobrando.

As checagens 3 e 5 sao as que um passe automatico nao faz sozinho: em 22/09 um
script cortou os bytes certos e mesmo assim decepou o sentido de 68 descricoes
(P-67.13). Tamanho nao e' criterio de qualidade.

Uso:
  p68_valida_retorno.py <lote.tsv> <lote_retorno.tsv> [...]
  p68_valida_retorno.py --todos <dir>
"""
import sys, csv, os, re, glob, argparse

CAUDA = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with',
         'from', 'and', 'or', 'but', 'that', 'which', 'who', 'whose', 'as',
         'is', 'are', 'was', 'were', 'be', 'been', 'its', 'this', 'these',
         'those', 'into', 'onto', 'over', 'under', 'than', 'then', 'when',
         'while', 'has', 'have', 'had', 'will', 'said', 'made', 'used',
         'very', 'more', 'most', 'such', 'so', 'his', 'her', 'their'}
INTOCAVEIS = ('id', 'cena', 'ordem', 'original', 'va_ponteiros', 'bytes_jp',
              'max_bytes')


def le(p):
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='\t'))


def tem_jp(t):
    return any('぀' <= c <= 'ヿ' or '一' <= c <= '鿿'
               or '＀' <= c <= '￯' for c in t)


def valida(orig_p, ret_p):
    orig = {r['id']: r for r in le(orig_p)}
    ret = le(ret_p)
    nome = os.path.basename(ret_p)
    erros, avisos, soma, teto = [], [], 0, 0
    tem_orcamento = any(o.get('max_bytes') for o in orig.values())

    for r in ret:
        k = r.get('id')
        o = orig.get(k)
        if o is None:
            erros.append((k, 'id nao existe no lote original'))
            continue
        for c in INTOCAVEIS:
            if (r.get(c) or '') != (o.get(c) or ''):
                erros.append((k, f'coluna {c} foi alterada'))
        t = (r.get('traducao') or '').strip()
        if not t:
            erros.append((k, 'traducao vazia'))
            continue
        try:
            b = t.encode('ascii')
        except UnicodeEncodeError as e:
            erros.append((k, f'nao e ASCII: {e.object[e.start:e.end]!r}'))
            continue
        if tem_jp(t):
            erros.append((k, 'sobrou japones na traducao'))
        if tem_orcamento:
            mx = int(o['max_bytes']) if o.get('max_bytes') else 0
            soma += len(b) + 1
            teto += mx + 1
            if mx and len(b) > mx:
                # AVISO, nao erro: `max_bytes` e' uma reparticao proporcional
                # do espaco do bloco, nao um limite fisico da linha. O que o
                # build exige e' que a SOMA caiba (checada abaixo).
                avisos.append((k, f'{len(b)} B acima do quinhao {mx} (soma decide)'))
        # `○○` e o nome do personagem do jogador, substituido em tempo de
        # execucao. Perder um deixa a frase sem sujeito em jogo (P-69).
        jp_marc = (o.get('original') or '').count(chr(9675)*2)
        if jp_marc and t.count('OO') + t.count(chr(9675)*2) < jp_marc:
            erros.append((k, f'perdeu o marcador de nome do jogador '
                             f'(original tem {jp_marc})'))
        # em bloco de varias linhas a quebra e LAYOUT: altura fixa da caixa
        nl_jp = (o.get('original') or '').count(chr(10))
        if nl_jp >= 2 and t.count(chr(10)) != nl_jp:
            erros.append((k, f'{t.count(chr(10))} quebras de linha, '
                             f'o original tem {nl_jp}'))
        # decapitada: so' cobra de quem e frase (tem espaco e e longo).
        # A pontuacao ESPELHA o japones: rotulo de menu nao termina em
        # 。/！/？ no original e nao deve ser cobrado em ingles — cobrar de
        # tudo reprovava texto que ja esta em jogo exatamente assim.
        jp = o.get('original') or ''
        jp_pontuado = jp.rstrip()[-1:] in '。！？.!?'
        if len(t) > 25 and ' ' in t:
            if jp_pontuado and t.rstrip()[-1:] not in '.!?)':
                erros.append((k, f'nao termina em pontuacao: ...{t[-30:]!r}'))
            pal = re.findall(r"[A-Za-z']+", t)
            if pal and pal[-1].lower() in CAUDA:
                erros.append((k, f'frase decapitada: ...{t[-32:]!r}'))

    print(f'\n=== {nome}: {len(ret)} linhas de {len(orig)} ===')
    if tem_orcamento:
        print(f'  bytes usados {soma} / orcamento {teto}  '
              f'{"OK" if soma <= teto else f"ESTOUROU {soma-teto} B"}')
    else:
        print('  sem limite de bytes (repointavel)')
    if avisos:
        print(f'  avisos (linha acima do quinhao, soma ainda cabe): {len(avisos)}')
        for k, m in avisos[:5]:
            print(f'    [{k}] {m}')
    print(f'  problemas: {len(erros)}')
    for k, m in erros[:15]:
        print(f'    [{k}] {m}')
    if len(erros) > 15:
        print(f'    ... e mais {len(erros)-15}')
    faltam = set(orig) - {r.get('id') for r in ret}
    if faltam:
        print(f'  {len(faltam)} linhas NAO devolvidas')
    ok = not erros and (not tem_orcamento or soma <= teto) and not faltam
    print(f'  -> {"ACEITO" if ok else "RECUSADO"}')
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('arquivos', nargs='*')
    ap.add_argument('--todos', metavar='DIR')
    args = ap.parse_args()

    pares = []
    if args.todos:
        for o in sorted(glob.glob(os.path.join(args.todos, '*.tsv'))):
            if o.endswith('_retorno.tsv'):
                continue
            r = o.replace('.tsv', '_retorno.tsv')
            if os.path.exists(r):
                pares.append((o, r))
            else:
                print(f'(sem retorno ainda: {os.path.basename(r)})')
    else:
        pares = list(zip(args.arquivos[::2], args.arquivos[1::2]))

    if not pares:
        print('nada a validar')
        return 0
    todos = [valida(o, r) for o, r in pares]
    print(f'\n{"TODOS ACEITOS" if all(todos) else "HA LOTE RECUSADO"}')
    return 0 if all(todos) else 1


if __name__ == '__main__':
    sys.exit(main())

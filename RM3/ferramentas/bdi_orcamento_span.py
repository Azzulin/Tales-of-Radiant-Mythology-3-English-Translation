#!/usr/bin/env python3
"""Mede, entrada por entrada do `namco.bdi`, se as cenas puladas caberiam com
UMA remontagem no fim em vez de uma por cena (P-81).

`bdi_build_iso.py` e' guloso e depende da ORDEM: percorre os arquivos na ordem
fisica do EZBIND e, para cada cena traduzida, tenta o buraco da propria cena e,
se nao couber, remonta a entrada inteira. O problema e' o instante da conta —
quando a cena 3 cresce 100 B, as cenas 40 a 90 ainda estao em japones, entao os
500 B que elas vao devolver (ingles em ASCII e' mais curto que EUC-JP) ainda nao
existem no blob. A cena 3 e' descartada por falta de um espaco que a propria
entrada teria minutos depois.

Esta ferramenta responde a pergunta certa: **somando TODAS as traducoes da
entrada de uma vez, cabe no span?** Se couber, a cena nao precisa de tradutor
nenhum — precisa de outra ordem de montagem.

Somente leitura. Nao escreve em ISO nenhuma.

Uso:
  bdi_orcamento_span.py <iso> <lba> <catalogo.csv> <dir_lotes> [--so-problema]
                        [--csv saida.csv]
"""
import sys, os, csv, gzip, struct, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import (ezbind_parse, alinhamento, fc_parse, fc_build,
                           carrega_mapas, carrega_traducoes, gzip_como_original)

SEC = 2048


def empacota(tamanhos, base, alin):
    """Tamanho total do EZBIND com estes dados, na mesma regra do remontador:
    dados em sequencia a partir de `base`, cada um alinhado a `alin`."""
    pos = base
    for t in tamanhos:
        pos += t
        pos += (-pos) % alin
    return pos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('lba', type=int)
    ap.add_argument('catalogo')
    ap.add_argument('dir_lotes')
    ap.add_argument('--so-problema', action='store_true',
                    help='lista so as entradas que nao cabem nem assim')
    ap.add_argument('--csv', default='')
    args = ap.parse_args()

    dados_dir = os.path.join(os.path.dirname(os.path.abspath(args.dir_lotes)), 'dados')
    idx = carrega_mapas(dados_dir)
    trad, _ = carrega_traducoes(args.dir_lotes, idx)
    print(f'traducoes carregadas: {len(trad)} cenas')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(args.catalogo, encoding='utf-8')):
        n = r['nome'].lower()
        if n.endswith('.scr') and n in trad:
            porv[int(r['entrada_v'])].add(n)
    print(f'{sum(len(v) for v in porv.values())} cenas traduziveis '
          f'em {len(porv)} entradas\n')

    base_iso = args.lba * SEC
    linhas = []
    st = collections.Counter()
    with open(args.iso, 'rb') as f:
        _, _, entries, _ = load_index(f, base_iso)
        pore = {e['v']: e for e in entries}
        feito = 0
        for v in sorted(porv):
            e = pore.get(v)
            if not e:
                continue
            f.seek(base_iso + e['off'])
            blob = f.read(e['span'])
            pe = ezbind_parse(blob)
            if not pe:
                continue
            count, cab_do, regs = pe
            alin = alinhamento(regs)
            base = min(r[3] for r in regs)

            orig, novo = [], []
            cresceu = collections.Counter()
            ordem = sorted(range(len(regs)), key=lambda k: regs[k][3])
            for k in ordem:
                nome, no, sz, do, key = regs[k]
                orig.append(sz)
                alvo = nome.lower()
                if alvo not in porv[v]:
                    novo.append(sz)
                    continue
                raw = blob[do:do + sz]
                try:
                    scr = gzip.decompress(raw)
                    p = fc_parse(scr)
                    tr = trad.get(alvo, {})
                    novas = [tr[i] if i in tr else s
                             for i, s in enumerate(p['strings'])]
                    gz = gzip_como_original(fc_build(p, novas), raw)
                except Exception:
                    novo.append(sz)
                    continue
                novo.append(len(gz))
                cresceu[alvo] = len(gz) - sz

            t_orig = empacota(orig, base, alin)
            t_novo = empacota(novo, base, alin)
            folga = e['span'] - t_novo
            st['entradas'] += 1
            st['cabe' if folga >= 0 else 'NAO_CABE'] += 1
            cres = sum(x for x in cresceu.values() if x > 0)
            enco = -sum(x for x in cresceu.values() if x < 0)
            linhas.append({'v': v, 'span': e['span'], 'pack_orig': t_orig,
                           'pack_novo': t_novo, 'folga': folga,
                           'cenas': len(porv[v]), 'bytes_a_mais': cres,
                           'bytes_a_menos': enco})
            feito += 1
            if feito % 200 == 0:
                print(f'  ... {feito}/{len(porv)} entradas', flush=True)

    print(f'\n{st["entradas"]} entradas medidas')
    print(f'  cabem empacotando tudo de uma vez : {st["cabe"]}')
    print(f'  NAO cabem nem assim               : {st["NAO_CABE"]}')

    ruins = sorted((L for L in linhas if L['folga'] < 0), key=lambda L: L['folga'])
    if ruins:
        print(f'\nentradas que estouram, da pior para a menos pior:')
        print(f'{"v":>6}{"span":>10}{"precisa":>10}{"falta":>9}{"cenas":>7}')
        for L in ruins[:30]:
            print(f'{L["v"]:>6}{L["span"]:>10}{L["pack_novo"]:>10}'
                  f'{-L["folga"]:>9}{L["cenas"]:>7}')
    apertadas = sorted((L for L in linhas if 0 <= L['folga'] < 4096),
                       key=lambda L: L['folga'])
    print(f'\n{len(apertadas)} entradas cabem com menos de 4 KB de folga '
          f'(as 10 mais apertadas):')
    for L in apertadas[:10]:
        print(f'   v{L["v"]:<6} folga {L["folga"]:>7} B  em {L["cenas"]} cenas')

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as o:
            w = csv.DictWriter(o, fieldnames=list(linhas[0]))
            w.writeheader(); w.writerows(linhas)
        print(f'\n-> {args.csv}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

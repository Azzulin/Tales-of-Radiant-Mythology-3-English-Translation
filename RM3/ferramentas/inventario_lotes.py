#!/usr/bin/env python3
"""Levantamento de TODOS os lotes do projeto: traduzido, devolvido, em jogo.

Ler as pastas de lote e cruzar com os artefatos de build responde tres coisas
que ficavam espalhadas por `ESTADO_DO_PROJETO.md` e pela memoria de quem
trabalhou: quanto ja voltou do tradutor, quanto disso esta preenchido de
verdade, e quanto ja entrou numa ISO.

Uso:
  inventario_lotes.py [--raiz .] [--csv saida.csv]

Para saber o que de fato chegou na ISO, leia `COBERTURA.md`: esta ferramenta
mede os LOTES, nao a ISO.
"""
import sys, os, csv, glob, json, re, collections, argparse

# ESTA FERRAMENTA NAO SABE O QUE ESTA NA ISO, e nao finge saber.
#
# Ate 25/09 ela deduzia isso da PASTA (`lotes/` = em jogo, `lotes_p68/` = fora)
# com um `ISO_ATUAL = 'en12'` fixo no codigo. Envelheceu mal: na `en18` as sete
# frentes de `lotes_p68/` ja estavam em jogo e a ferramenta seguia dizendo "NAO
# reinserido". Pasta e' onde o lote MORA, nao onde ele CHEGOU.
#
# Quem responde "o que chegou na ISO" e' a medicao na propria ISO
# (`bdi_cobertura.py`, `eboot_cobertura.py`), consolidada em `COBERTURA.md`.
# Aqui a pergunta e outra, e mais modesta: quanto voltou do tradutor e quanto
# disso esta preenchido de verdade.
PASTAS = ('lotes', 'lotes_p68', 'lotes_bancos')


def falas(p):
    """(total, com traducao) de um .tsv de lote."""
    try:
        with open(p, encoding='utf-8') as f:
            rs = list(csv.DictReader(f, delimiter='\t'))
    except Exception:
        return 0, 0
    if not rs:
        return 0, 0
    col = 'traducao' if 'traducao' in rs[0] else None
    tot = len(rs)
    tr = sum(1 for r in rs if col and (r.get(col) or '').strip()) if col else 0
    return tot, tr


def frente(nome):
    m = re.match(r'^([A-Za-z]+)', nome)
    return m.group(1).upper() if m else '?'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raiz', default='.')
    ap.add_argument('--csv', default='')
    args = ap.parse_args()

    linhas = []
    for pasta in PASTAS:
        d = os.path.join(args.raiz, pasta)
        if not os.path.isdir(d):
            continue
        for p in sorted(glob.glob(os.path.join(d, '*.tsv'))):
            base = os.path.basename(p)
            if base.endswith('_retorno.tsv'):
                continue
            nome = base[:-4]
            ret = p[:-4] + '_retorno.tsv'
            tot, _ = falas(p)
            if os.path.exists(ret):
                rtot, rtr = falas(ret)
                estado = 'devolvido'
            else:
                rtot = rtr = 0
                estado = 'PENDENTE'
            linhas.append({
                'pasta': pasta, 'lote': nome, 'frente': frente(nome),
                'falas': tot, 'devolvidas': rtot, 'traduzidas': rtr,
                'estado': estado,
            })

    # lotes VAL (formato JSON, outro fluxo)
    for p in sorted(glob.glob(os.path.join(args.raiz, 'dados',
                                           'item_equip_shrink', 'VAL-*.json'))):
        if p.endswith('_out.json'):
            continue
        nome = os.path.basename(p)[:-5]
        d = json.load(open(p, encoding='utf-8'))
        out = p[:-5] + '_out.json'
        if os.path.exists(out):
            n = len(json.load(open(out, encoding='utf-8')))
            estado = 'devolvido'
        else:
            n = 0
            estado = 'PENDENTE'
        linhas.append({'pasta': 'item_equip_shrink', 'lote': nome,
                       'frente': 'VAL', 'falas': d.get('n_itens', 0),
                       'devolvidas': n, 'traduzidas': n, 'estado': estado})

    # ---------- por frente ----------
    porf = collections.OrderedDict()
    for L in linhas:
        chave = (L['frente'], L['pasta'])
        f = porf.setdefault(chave, collections.Counter())
        f['lotes'] += 1
        f['falas'] += L['falas']
        f['traduzidas'] += L['traduzidas']
        f['pendentes'] += 1 if L['estado'] == 'PENDENTE' else 0

    print(f'{"frente":<8}{"lotes":>6}{"falas":>9}{"traduzidas":>12}'
          f'{"pend":>6}  situacao')
    print('-' * 62)
    tl = tf = tt = tp = 0
    for (f, pasta), c in sorted(porf.items(), key=lambda kv: -kv[1]['falas']):
        tl += c['lotes']; tf += c['falas']
        tt += c['traduzidas']; tp += c['pendentes']
        if c['pendentes']:
            sit = f'{c["pendentes"]} lote(s) sem retorno'
        elif c['traduzidas'] < c['falas']:
            sit = f'devolvido, {c["falas"] - c["traduzidas"]} linha(s) em branco'
        else:
            sit = 'devolvido e preenchido'
        print(f'{f:<8}{c["lotes"]:>6}{c["falas"]:>9}{c["traduzidas"]:>12}'
              f'{c["pendentes"]:>6}  {sit}')
    print('-' * 62)
    print(f'{"TOTAL":<8}{tl:>6}{tf:>9}{tt:>12}{tp:>6}')

    pend = [L for L in linhas if L['estado'] == 'PENDENTE']
    print(f'\nlotes sem retorno: {len(pend)}')
    for L in pend:
        print(f'   {L["pasta"]}/{L["lote"]}  ({L["falas"]} falas)')

    # devolvidos mas com buraco
    furo = [L for L in linhas if L['estado'] == 'devolvido'
            and L['traduzidas'] < L['devolvidas']]
    if furo:
        print(f'\ndevolvidos com linha em branco: {len(furo)}')
        for L in furo:
            print(f'   {L["lote"]}: {L["traduzidas"]}/{L["devolvidas"]}')

    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as o:
            w = csv.DictWriter(o, fieldnames=list(linhas[0]))
            w.writeheader(); w.writerows(linhas)
        print(f'\n-> {args.csv}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

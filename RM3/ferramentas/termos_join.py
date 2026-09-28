#!/usr/bin/env python3
"""Junta a colheita crua (termos_ui_guia_cru.csv) ao dicionario (dic_ui_rm3.psv)
e AUDITA os bytes. Nunca conta caracteres.

Uso: termos_join.py <cru.csv> <dic.psv> <saida.csv>
"""
import sys, csv

ENC = 'euc_jp'
LIM = {'ab_7': 7, 'ab_5': 5, 'ab_3': 3}


def main():
    cru, dic, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    # chave normalizada: o guia tem uma string com quebra de linha REAL no meio
    # (P-27: fim de linha e LF de verdade). A chave do dicionario e' sem a quebra.
    def norm(s):
        return s.replace('\r', '').replace('\n', '')

    crus = {}
    ordem = []
    bruto = {}
    for r in csv.DictReader(open(cru, encoding='utf-8')):
        k = norm(r['origem_jp'])
        bruto[k] = r['origem_jp']
        crus[k] = r
        ordem.append(k)
    d = {}
    with open(dic, encoding='utf-8') as fh:
        cab = fh.readline().rstrip('\n').split('|')
        for ln, linha in enumerate(fh, 2):
            linha = linha.rstrip('\n')
            if not linha.strip():
                continue
            c = linha.split('|')
            if len(c) != len(cab):
                print(f'! dic linha {ln}: {len(c)} campos, esperado {len(cab)}', file=sys.stderr)
                continue
            reg = dict(zip(cab, c))
            d[norm(reg['origem_jp'])] = reg

    faltam = [k for k in ordem if k not in d]
    sobram = [k for k in d if k not in crus]
    prob = []

    cols = ['origem_jp', 'bytes_jp', 'ocorrencias', 'categoria', 'canonico_en',
            'bytes_canonico', 'folga_vs_jp', 'ab_7', 'ab_5', 'ab_3',
            'fonte', 'status', 'nota', 'contexto_1']
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for k in ordem:
            r = crus[k]
            reg = d.get(k)
            if not reg:
                continue
            bjp = int(r['bytes_jp'])
            can = reg['canonico_en']
            bcan = len(can.encode('ascii', 'replace'))
            linha = {'origem_jp': bruto[k], 'bytes_jp': bjp, 'ocorrencias': r['ocorrencias'],
                     'categoria': reg['categoria'], 'canonico_en': can,
                     'bytes_canonico': bcan, 'folga_vs_jp': bjp - bcan,
                     'fonte': reg['fonte'], 'status': reg['status'],
                     'nota': reg['nota'], 'contexto_1': r['contexto_1']}
            for c, lim in LIM.items():
                v = reg[c]
                linha[c] = v
                if v == '-':
                    continue
                n = len(v.encode('ascii', 'replace'))
                if n > lim:
                    prob.append(f'{k}: {c}="{v}" tem {n} bytes, limite {lim}')
                if not all(32 <= b < 127 for b in v.encode('ascii', 'replace')):
                    prob.append(f'{k}: {c}="{v}" fora do ASCII imprimivel')
            if not all(32 <= b < 127 for b in can.encode('ascii', 'replace')):
                prob.append(f'{k}: canonico "{can}" fora do ASCII imprimivel')
            w.writerow(linha)

    # relatorio
    print(f'colhidos={len(ordem)} no_dicionario={len(d)} escritos={len(ordem)-len(faltam)}')
    if faltam:
        print(f'SEM TRADUCAO ({len(faltam)}): ' + ' '.join(faltam))
    if sobram:
        print(f'NO DICIONARIO MAS NAO COLHIDOS ({len(sobram)}): ' + ' '.join(sobram))
    if prob:
        print(f'VIOLACOES DE BYTES ({len(prob)}):')
        for p in prob:
            print('  ' + p)
    else:
        print('bytes: 0 violacoes')
    # estouro do canonico contra o japones
    est = 0
    for k in ordem:
        if k in d and int(crus[k]['bytes_jp']) - len(d[k]['canonico_en'].encode('ascii', 'replace')) < 0:
            est += 1
    print(f'canonico maior que o japones em {est} de {len(ordem)} termos')
    return 1 if (faltam or sobram or prob) else 0


if __name__ == '__main__':
    sys.exit(main())

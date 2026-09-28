#!/usr/bin/env python3
"""Monta o lote da tela de criacao de personagem e AUDITA bytes e largura.

Uso: lote_criacao.py <eboot_dec> <trad.psv> <saida.csv>

As series numeradas (padroes de cabelo, olho, boca, voz, opcoes) sao GERADAS,
nao digitadas — 111 das 198 linhas. Menos digitacao, zero erro de sequencia.
Somente leitura no binario.
"""
import sys, csv, re
import eboot_tabsis as T

INI_TAB = 0x08D65738      # indice 30 da tabela que comeca em 0x08D656C0
N = 198
LARG_MAX = 42             # P-33: 42 caracteres ASCII por linha na caixa

# series geradas: (id_inicial, quantidade, molde)
SERIES = [(104, 20, 'Hair Pattern {}'), (125, 15, 'Option {}'),
          (150, 30, 'Eye Pattern {}'), (180, 20, 'Mouth Pattern {}'),
          (200, 6, 'Pattern {}'), (206, 20, 'Voice Pattern {}')]

FW = str.maketrans('０１２３４５６７８９', '0123456789')


def carrega_trad(caminho):
    d = {}
    for ln, linha in enumerate(open(caminho, encoding='utf-8'), 1):
        linha = linha.rstrip('\n')
        if not linha.strip():
            continue
        c = linha.split('|')
        assert len(c) == 5, f'{caminho}:{ln} tem {len(c)} campos, esperado 5'
        d[int(c[0])] = {'traducao': c[1].replace('\\n', '\n'),
                        'fonte': c[2], 'status': c[3], 'nota': c[4]}
    for ini, qtd, molde in SERIES:
        for k in range(qtd):
            i = ini + k
            assert i not in d, f'id {i} digitado E gerado — conflito'
            d[i] = {'traducao': molde.format(k + 1), 'fonte': 'gerado',
                    'status': 'revisar', 'nota': f'serie {molde.format("N")}'}
    return d


def main():
    eb, psv, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    d = T.ler(eb)
    ents = T.entradas(d, INI_TAB, N)
    trad = carrega_trad(psv)

    ids = {e['i'] + 30 for e in ents}          # o indice 0 aqui e' o 30 da tabela mae
    faltam = sorted(ids - set(trad))
    sobram = sorted(set(trad) - ids)
    prob = []

    a_ini, a_fim, a_tam = T.arena(ents)
    soma_jp = 0
    soma_en = 0
    linhas = []
    for e in ents:
        i = e['i'] + 30
        t = trad.get(i)
        if t is None or e['off'] is None:
            continue
        b = e['original']
        jp = b.decode('euc_jp')
        en = t['traducao']
        try:
            eb_bytes = en.encode('ascii')
        except UnicodeEncodeError:
            prob.append(f'{i}: traducao fora do ASCII')
            eb_bytes = en.encode('ascii', 'replace')
        soma_jp += len(b) + 1
        soma_en += len(eb_bytes) + 1

        # control codes: mesmo conjunto, mesma quantidade, mesma ordem
        cc_jp = re.findall(r'%[sd]|\n|\t', jp)
        cc_en = re.findall(r'%[sd]|\n|\t', en)
        if [c for c in cc_jp if c not in '\n\t'] != [c for c in cc_en if c not in '\n\t']:
            prob.append(f'{i}: tokens %s/%d divergem: jp={cc_jp} en={cc_en}')
        if jp.count('\n') != en.count('\n'):
            prob.append(f'{i}: quebras de linha: jp={jp.count(chr(10))} en={en.count(chr(10))}')

        larguras = [len(l) for l in en.split('\n')]
        if max(larguras) > LARG_MAX:
            prob.append(f'{i}: linha de {max(larguras)} caracteres, maximo {LARG_MAX}')

        slot = T.slot_de(d, e['va_string'], e['bytes'])
        linhas.append({
            'id': i, 'va_ponteiro': f'0x{e["va_ponteiro"]:08X}',
            'va_string': f'0x{e["va_string"]:08X}', 'off_arquivo': e['off'],
            'bytes_jp': len(b), 'slot_inplace': slot,
            'cabe_inplace': 'sim' if len(eb_bytes) <= slot else 'NAO',
            'control_codes': ' '.join(c.replace('\n', 'LF').replace('\t', 'TAB') for c in cc_jp),
            'original': jp.replace('\n', '\\n'),
            'traducao': en.replace('\n', '\\n'),
            'bytes_usados': len(eb_bytes),
            'largura_max': max(larguras),
            'fonte': t['fonte'], 'status': t['status'], 'nota': t['nota'],
        })

    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'linhas={len(linhas)}  arena=0x{a_ini:08X}..0x{a_fim:08X} ({a_tam} B)')
    print(f'japones + NUL = {soma_jp} B   ingles + NUL = {soma_en} B   '
          f'diferenca = {soma_en - soma_jp:+d} B')
    print(f'ARENA: {a_tam} B disponiveis, {soma_en} B necessarios -> '
          f'{"CABE" if soma_en <= a_tam else "ESTOURA"} (folga {a_tam - soma_en:+d} B)')
    nao = [r for r in linhas if r['cabe_inplace'] == 'NAO']
    print(f'in-place sem repontear: {len(linhas)-len(nao)} cabem, {len(nao)} nao cabem')
    if faltam:
        print(f'SEM TRADUCAO ({len(faltam)}): {faltam}')
    if sobram:
        print(f'TRADUCAO SEM STRING ({len(sobram)}): {sobram}')
    if prob:
        print(f'PROBLEMAS ({len(prob)}):')
        for p in prob:
            print('  ' + p)
    else:
        print('control codes, quebras de linha e largura: 0 problemas')
    return 1 if (faltam or sobram or prob or soma_en > a_tam) else 0


if __name__ == '__main__':
    sys.exit(main())

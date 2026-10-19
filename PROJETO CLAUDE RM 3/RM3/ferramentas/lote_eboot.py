#!/usr/bin/env python3
"""Monta e audita um lote de blocos do EBOOT (P-42/P-43). Somente leitura.

Uso: lote_eboot.py <eboot_dec> <trad.psv> <saida.csv> [--sem-largura]

PSV: bloco|va_ponteiro|traducao|fonte|status|nota
  - traducao vazia = MANTER os bytes originais verbatim (glifo, nome de arquivo)
  - \\n na traducao = quebra de linha real
  - ponteiros do mesmo bloco que produzem os MESMOS bytes sao deduplicados:
    uma string no pool, varios ponteiros (P-42.3)

--sem-largura desliga a checagem de 42 caracteres/linha (LARG_MAX). Use para
blocos SIS-NN (P-54): eles vivem numa arena reponteavel, nao na caixa de
dialogo 3x42 — a mesma distincao que `valida_retorno.py --sem-largura` ja faz
para esses lotes antes deles chegarem aqui. Sem a flag, comportamento
inalterado (o bloco `criacao`, tela de personagem, usa a caixa e continua
precisando do limite).
"""
import sys, csv, re, collections
import eboot_tabsis as T

LARG_MAX = 42


def carrega(psv):
    rows = []
    fh = open(psv, encoding='utf-8')
    cab = fh.readline().rstrip('\n').split('|')
    for ln, linha in enumerate(fh, 2):
        linha = linha.rstrip('\n')
        if not linha.strip():
            continue
        c = linha.split('|')
        assert len(c) == len(cab), f'{psv}:{ln} tem {len(c)} campos, esperado {len(cab)}'
        rows.append(dict(zip(cab, c)))
    fh.close()
    return rows


def main():
    sem_largura = '--sem-largura' in sys.argv
    pos = [a for a in sys.argv[1:] if not a.startswith('--')]
    d = T.ler(pos[0])
    rows = carrega(pos[1])
    saida = pos[2]
    prob = []
    linhas = []
    blocos = collections.OrderedDict()
    for r in rows:
        blocos.setdefault(r['bloco'], []).append(r)

    for nome, rs in blocos.items():
        ents = []
        for r in rs:
            vp = int(r['va_ponteiro'], 16)
            e = T.entradas(d, vp, 1)[0]
            if e['off'] is None:
                prob.append(f'{nome} 0x{vp:08X}: nao e ponteiro')
                continue
            e['row'] = r
            ents.append(e)
        a_ini, a_fim, a_tam = T.arena(ents)

        pool = 0
        vistos = {}
        for e in ents:
            r = e['row']
            jp = e['original'].decode('euc_jp')
            if r['traducao'] == '':
                novo = e['original']
                manter = True
            else:
                manter = False
                txt = r['traducao'].replace('\\n', '\n')
                try:
                    novo = txt.encode('ascii')
                except UnicodeEncodeError:
                    prob.append(f'{nome} 0x{e["va_ponteiro"]:08X}: traducao fora do ASCII')
                    novo = txt.encode('ascii', 'replace')
                cc_jp = re.findall(r'%[sd0-9]*[sdKB]?', jp)
                for tok in ('%s', '%d'):
                    if jp.count(tok) != txt.count(tok):
                        prob.append(f'{nome} 0x{e["va_ponteiro"]:08X}: {tok} '
                                    f'jp={jp.count(tok)} en={txt.count(tok)}')
                if jp.count('\n') != txt.count('\n'):
                    prob.append(f'{nome} 0x{e["va_ponteiro"]:08X}: quebras de linha '
                                f'jp={jp.count(chr(10))} en={txt.count(chr(10))}')
                if not sem_largura:
                    larg = max(len(l) for l in txt.split('\n'))
                    if larg > LARG_MAX:
                        prob.append(f'{nome} 0x{e["va_ponteiro"]:08X}: linha de {larg} '
                                    f'caracteres, maximo {LARG_MAX}')
            if novo not in vistos:
                vistos[novo] = True
                pool += len(novo) + 1
            slot = T.slot_de(d, e['va_string'], e['bytes'])
            linhas.append({
                'bloco': nome, 'va_ponteiro': f'0x{e["va_ponteiro"]:08X}',
                'va_string': f'0x{e["va_string"]:08X}',
                'off_arquivo': e['off'], 'bytes_jp': e['bytes'], 'slot_inplace': slot,
                'manter': 'sim' if manter else '',
                'control_codes': ' '.join(sorted(set(
                    ([f'%s x{jp.count("%s")}'] if '%s' in jp else []) +
                    ([f'%d x{jp.count("%d")}'] if '%d' in jp else []) +
                    ([f'LF x{jp.count(chr(10))}'] if '\n' in jp else [])))),
                'original': jp.replace('\n', '\\n'),
                'traducao': (r['traducao'] if not manter else '(verbatim)'),
                'bytes_usados': len(novo),
                'fonte': r['fonte'], 'status': r['status'], 'nota': r['nota'],
            })
        cabe = pool <= a_tam
        print(f'[{nome}] {len(ents)} ponteiros, {len(vistos)} strings distintas '
              f'(dedup -{len(ents)-len(vistos)})')
        print(f'  arena 0x{a_ini:08X}..0x{a_fim:08X} = {a_tam} B   '
              f'pool novo = {pool} B   -> {"CABE" if cabe else "ESTOURA"} '
              f'(folga {a_tam-pool:+d})')
        if not cabe:
            prob.append(f'{nome}: pool de {pool} B nao cabe em arena de {a_tam} B')

    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)
    print(f'\n{len(linhas)} linhas -> {saida}')
    if prob:
        print(f'PROBLEMAS ({len(prob)}):')
        for p in prob:
            print('  ' + p)
        return 1
    print('control codes, quebras de linha, largura, ASCII e arena: 0 problemas')
    return 0


if __name__ == '__main__':
    sys.exit(main())

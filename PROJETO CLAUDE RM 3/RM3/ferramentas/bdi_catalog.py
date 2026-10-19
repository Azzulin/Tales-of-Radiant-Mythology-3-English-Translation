#!/usr/bin/env python3
"""Catalogo completo do namco.bdi: uma linha por arquivo logico, com nome real.

Uso: bdi_catalog.py <iso> <lba> <size> <saida.csv>

Recebe: a ISO (somente leitura).
Devolve: CSV com entrada_v, tipo, nome, tamanho, offset absoluto no bdi, chave.
Valida: o indice inteiro antes de catalogar; aborta se qualquer checagem falhar.
Falha em seguranca: nao escreve nada fora do CSV pedido; nunca toca a ISO.
"""
import sys, csv
from bdi import load_index, validate, parse_ezbind, gzip_name, classify, SEC


def main():
    iso, lba, size, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    base = lba * SEC
    with open(iso, 'rb') as f:
        buckets, count, entries, sentinel = load_index(f, base)
        bad = validate(buckets, count, entries, sentinel, size)
        if bad:
            print('INDICE INVALIDO — abortando:')
            for b in bad:
                print('  -', b)
            return 1
        print(f'indice valido: {count} entradas, sentinela=0x{sentinel:x}')

        rows, stat = [], {}
        for e in entries:
            f.seek(base + e['off'])
            tipo = classify(f.read(16))
            stat[tipo] = stat.get(tipo, 0) + 1
            if tipo == 'EZBIND':
                ez = parse_ezbind(f, base, e['off'], e['span'])
                if ez:
                    for fi in ez['files']:
                        rows.append([e['v'], 'EZBIND', fi['name'], fi['size'],
                                     e['off'] + fi['data_off'], f'{fi["key"]:08x}'])
                    continue
                tipo = 'EZBIND(ilegivel)'
            nm = gzip_name(f, base, e['off']) if tipo == 'gzip' else ''
            rows.append([e['v'], tipo, nm or '', e['span'], e['off'], f'{e["key"]:08x}'])

        with open(out, 'w', newline='', encoding='utf-8') as o:
            w = csv.writer(o)
            w.writerow(['entrada_v', 'tipo', 'nome', 'tamanho', 'off_bdi', 'chave'])
            w.writerows(rows)
        print(f'{len(rows)} arquivos logicos -> {out}')
        print('tipos das 7344 entradas de topo:',
              dict(sorted(stat.items(), key=lambda kv: -kv[1])))
        nomeados = sum(1 for r in rows if r[2])
        print(f'com nome real: {nomeados} de {len(rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

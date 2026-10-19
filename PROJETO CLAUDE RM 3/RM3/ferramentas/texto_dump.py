#!/usr/bin/env python3
"""Dumpa as frentes OLDATA e PTRTAB para a tabela de strings do projeto.

Uso: texto_dump.py <saida.csv> <arquivo> [...]
     Detecta gzip, e escolhe o parser pelo formato (OLDATA vs PTRTAB).

Valida round-trip byte-perfeito antes de dumpar; arquivo que falhar e' recusado
inteiro. Nenhuma string entra na tabela sem decodificar em EUC-JP.
"""
import sys, csv, gzip, os, struct
import oldata, ptrtab


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    rows, bad = [], []
    for p in paths:
        raw = open(p, 'rb').read()
        if raw[:3] == b'\x1f\x8b\x08':
            raw = gzip.decompress(raw)
        nome = os.path.basename(p)
        # OLDATA: off_titulos == 12 + count*12
        count = struct.unpack_from('<I', raw, 0)[0]
        try:
            t_off = struct.unpack_from('<I', raw, 4)[0]
        except Exception:
            t_off = -1
        if t_off == 12 + count * 12:
            if not oldata.round_trip_ok(raw):
                bad.append((nome, 'OLDATA round-trip falhou')); continue
            pr = oldata.parse(raw)
            for i, t in enumerate(pr['titulos']):
                rows.append([f'{nome}:titulo:{i}', nome, i, len(t), t.decode(oldata.ENC), '',
                             0, '', 'pendente', f'episodio {i}, sem limite de bytes'])
            for i, l in enumerate(pr['narracao']):
                rows.append([f'{nome}:narracao:{i}', nome, i, len(l), l.decode(oldata.ENC), '',
                             0, '', 'pendente', 'narracao, sem limite de bytes'])
            print(f'{nome}: OLDATA ok — {len(pr["titulos"])} titulos + {len(pr["narracao"])} linhas')
            continue
        # PTRTAB
        if not ptrtab.round_trip_ok(raw):
            bad.append((nome, 'PTRTAB round-trip falhou')); continue
        pr = ptrtab.parse(raw)
        for i, s in enumerate(pr['strings']):
            rows.append([f'{nome}:{i}', nome, i, len(s), s.decode(ptrtab.ENC), '',
                         0, 'LF' if b'\n' in s else '', 'pendente', 'sem limite de bytes'])
        print(f'{nome}: PTRTAB ok — {pr["count"]} strings')

    with open(out, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['id', 'arquivo', 'offset', 'bytes_max', 'original', 'traducao',
                    'bytes_usados', 'control_codes', 'status', 'nota'])
        w.writerows(rows)
    print(f'{len(rows)} strings -> {out}')
    for b in bad:
        print('  RECUSADO:', b)


if __name__ == '__main__':
    main()

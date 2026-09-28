#!/usr/bin/env python3
"""Dumpa arquivos TXZ para a tabela de strings do projeto.

Uso: txz_dump.py <saida.csv> <arquivo.txz|.bin descomprimido> [...]
     txz_dump.py <saida.csv> --gz <arquivo.txz comprimido> [...]

Colunas (padrao do projeto): id, arquivo, offset, bytes_max, original,
traducao, bytes_usados, control_codes, status, nota.

`bytes_max` = bytes_usados: o formato **nao tem folga**. Mudar tamanho exige
reescrever a tabela de ponteiros do arquivo (o build() do txz.py faz isso) e,
depois, a cadeia gzip -> EZBIND -> indice do BDI.

Valida round-trip byte-perfeito de cada arquivo antes de dumpar; se falhar,
aquele arquivo e' recusado (nunca dumpa parcial).
"""
import sys, csv, gzip, os, re
import txz

TAG = re.compile(r'\[[^\]]{1,20}\]|\\n')


def main():
    out = sys.argv[1]
    args = sys.argv[2:]
    gz = '--gz' in args
    paths = [a for a in args if a != '--gz']
    rows, bad = [], []
    for p in paths:
        raw = open(p, 'rb').read()
        if gz or raw[:3] == b'\x1f\x8b\x08':
            raw = gzip.decompress(raw)
        try:
            if not txz.round_trip_ok(raw):
                bad.append((p, 'round-trip falhou')); continue
            pr = txz.parse(raw)
        except Exception as e:
            bad.append((p, str(e))); continue
        nome = os.path.basename(p)
        for s in pr['strings']:
            try:
                orig = txz.decode(s['raw'])
            except UnicodeDecodeError as e:
                bad.append((f'{nome}#{s["i"]}', f'shift_jis: {e}')); orig = ''
            cc = '|'.join(TAG.findall(orig))
            rows.append([f'{nome}:{s["i"]}', nome, s['off'], s['bytes'], orig, '',
                         0, cc, 'pendente', f'id_jogo={s["id"]}'])
    with open(out, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['id', 'arquivo', 'offset', 'bytes_max', 'original', 'traducao',
                    'bytes_usados', 'control_codes', 'status', 'nota'])
        w.writerows(rows)
    print(f'{len(rows)} strings -> {out}')
    if bad:
        print('RECUSADOS:')
        for b in bad: print('  ', b)


if __name__ == '__main__':
    main()

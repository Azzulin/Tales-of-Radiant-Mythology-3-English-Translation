#!/usr/bin/env python3
"""Extrai as falas japonesas das cenas `.scr` que `bdi_cobertura.py` achou sem
extracao, e monta o lote de traducao.

Fecha o outro lado da conferencia do P-68: no `namco.bdi` sobraram 115 falas em
65 cenas (quase todas `mapD`, texto de placa/campo) — as outras 495 cenas nunca
extraidas estao vazias.

Somente leitura, e so' na ISO original.

Uso:
  bdi_cobertura_extrai.py <iso> <lba> <catalogo.csv> <cobertura.csv> <saida.tsv>
"""
import sys, csv, collections, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_cobertura import cenas_do_blob, tem_jp
import facechat

SEC = 2048


def main():
    iso, lba, cat, cob, out = (sys.argv[1], int(sys.argv[2]), sys.argv[3],
                               sys.argv[4], sys.argv[5])

    alvo = {r['cena'] for r in csv.DictReader(open(cob, encoding='utf-8'))
            if r['ja_extraida'] == 'NAO' and int(r['falas_jp']) > 0}
    print(f'{len(alvo)} cenas a extrair')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n in alvo:
            porv[int(r['entrada_v'])].add(n)

    base = lba * SEC
    linhas = []
    with open(iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        for v in sorted(porv):
            e = pore.get(v)
            if not e:
                continue
            f.seek(base + e['off'])
            achadas = cenas_do_blob(f.read(min(e['span'], 8 << 20)))
            for nome in sorted(porv[v]):
                blob = achadas.get(nome)
                if blob is None:
                    continue
                if not facechat.round_trip_ok(blob):
                    print(f'  round-trip falhou: {nome} — pulada')
                    continue
                p = facechat.parse(blob)
                for i, s in enumerate(p['strings']):
                    if not tem_jp(s):
                        continue
                    try:
                        t = s.decode('euc_jp')
                    except Exception:
                        continue
                    linhas.append([f'{nome}#{i}', nome, i, '(campo)', '(field)',
                                   'campo', '', t, '', '', len(s)])

    with open(out, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o, delimiter='\t')
        w.writerow(['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
                    'control_codes', 'original', 'traducao', 'nota_do_tradutor',
                    'bytes_jp'])
        w.writerows(linhas)
    print(f'{len(linhas)} falas -> {out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Monta os lotes de traducao dos bancos do BDI que estavam extraidos e nunca
traduzidos (P-69): sinopse, titulos de capitulo, titulos de skit do BDI e as
duas biografias de personagem.

Le as tabelas de extracao que ja existem (`strings_historia.csv`,
`strings_bancos_novos.csv` — so' o japones; a coluna `traducao` delas sempre
esteve vazia) e escreve um `.tsv` por lote no mesmo formato dos outros.

**Calcula `max_bytes` a partir do espaco MEDIDO no container**, nao do tamanho
da string. Esta e' a licao do `valuables` (P-67.14): traduzir primeiro e medir
depois custou 385 descricoes devolvidas ao japones.

Espaco medido em 23/09/2026, direto da ISO:

  v2063  campo FIXO de 64 B por registro -> 63 B por titulo, garantidos.
         O arquivo nao cresce: o numero de registros nao muda.
  v2069  cru, 44.997 B usados em span de 45.056  -> folga 59 B (1,02x)
  v2070  GZIP, 43.552 B descomprimidos em span comprimido de 20.480 (1,01x).
         Ingles ASCII comprime melhor que EUC-JP, entao ha margem extra aqui.
  ORG    EZBIND, 21.491 B com buraco de 21.492   -> 1,02x
  TOW3   EZBIND, 18.591 B com buraco de 19.412   -> 1,07x

Uso:
  bancos_gera_lotes.py [--saida lotes_bancos] [--teto 320]
"""
import sys, os, csv, collections, argparse

# banco -> (rotulo do lote, espaco em bytes ou None se campo fixo, teto fixo)
BANCOS = {
    'v2063 (titulos de skit)':      ('SKITBDI', None, 63),
    'v2069 (sinopse)':              ('SINOPSE', 45056, None),
    'v2070_oldata.bin':             ('CAPITULO', 43552, None),
    'v3082_CharGuideTextORG.bin':   ('PERFIL-ORG', 21492, None),
    'v3082_CharGuideTextTOW3.bin':  ('PERFIL-TOW3', 19412, None),
}
COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
        'control_codes', 'original', 'traducao', 'nota_do_tradutor',
        'offset_arquivo', 'bytes_jp', 'max_bytes']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--saida', default='lotes_bancos')
    ap.add_argument('--teto', type=int, default=320)
    ap.add_argument('--dados', default='dados')
    args = ap.parse_args()

    por = collections.defaultdict(list)
    for f in ('strings_historia', 'strings_bancos_novos'):
        p = os.path.join(args.dados, f + '.csv')
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['arquivo'] in BANCOS and r['original'].strip():
                por[r['arquivo']].append(r)

    os.makedirs(args.saida, exist_ok=True)
    manifesto = []
    for banco, (rot, espaco, fixo) in BANCOS.items():
        rs = por.get(banco, [])
        if not rs:
            print(f'{banco}: nenhuma string — pulado')
            continue
        jp = [len(r['original'].encode('euc_jp', 'replace')) for r in rs]
        total_jp = sum(n + 1 for n in jp)

        if fixo:
            orc = [fixo] * len(rs)
        else:
            fator = espaco / total_jp
            orc = [max(4, int((n + 1) * fator) - 1) for n in jp]

        linhas = []
        for i, (r, b, m) in enumerate(zip(rs, jp, orc)):
            linhas.append([f'{rot.lower()}#{i}', banco, i, '(banco)', '(bank)',
                           'sistema', r.get('control_codes', ''),
                           r['original'], '', '',
                           r.get('offset', ''), b, m])
        partes = [linhas[i:i + args.teto] for i in range(0, len(linhas), args.teto)]
        for k, parte in enumerate(partes, 1):
            nome = f'{rot}-{k:02d}' if len(partes) > 1 else rot
            cam = os.path.join(args.saida, f'{nome}.tsv')
            with open(cam, 'w', newline='', encoding='utf-8') as fh:
                w = csv.writer(fh, delimiter='\t')
                w.writerow(COLS)
                w.writerows(parte)
            print(f'-> {cam}  {len(parte)} falas')
        manifesto.append((rot, banco, len(rs), total_jp,
                          espaco if espaco else fixo * len(rs),
                          sum(m + 1 for m in orc)))

    print(f'\n{"lote":<13}{"falas":>7}{"bytes JP":>10}{"espaco":>9}{"orcamento":>11}{"razao":>8}')
    print('-' * 60)
    for rot, banco, n, jp, esp, orc in manifesto:
        print(f'{rot:<13}{n:>7}{jp:>10}{esp:>9}{orc:>11}{esp/jp:>7.2f}x')
    cam = os.path.join(args.saida, '00_MANIFESTO.csv')
    with open(cam, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['lote', 'banco', 'falas', 'bytes_jp', 'espaco', 'orcamento_en'])
        for m in manifesto:
            w.writerow(m)
    print(f'\n-> {cam}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

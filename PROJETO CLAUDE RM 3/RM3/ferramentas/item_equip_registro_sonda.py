#!/usr/bin/env python3
"""Sonda o formato de registro de UMA categoria do banco de item/equipamento (P-67.8/67.9).

So' leitura. Nao decide nada sozinho — imprime, pra leitura humana, onde cada
uma das primeiras N strings distintas de uma categoria e' referenciada como
ponteiro cru (4 bytes LE) em QUALQUER lugar do EBOOT. E' o mesmo metodo de
forca bruta que achou o formato de `consumivel`/`head_equip` em P-67.3, só que
aqui automatizado pra qualquer categoria.

Uso: item_equip_registro_sonda.py <eboot_dec> <categoria_en> [--n N]

`categoria_en` e' a coluna `cena` de dados/item_equip_falantes.tsv (ex.:
consumable, head_equip, sword_1h...). `--n` (default 12) e' quantas strings
distintas, em ordem de varredura da arena, mostrar.
"""
import sys, csv, struct, argparse

DELTA = 0x08803000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('categoria')
    ap.add_argument('--n', type=int, default=12)
    ap.add_argument('--falantes', default='dados/item_equip_falantes.tsv')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    with open(args.falantes, encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter='\t')
        sub = [row for row in r if row['cena'] == args.categoria]
    if not sub:
        print(f'ERRO: nenhuma linha com cena={args.categoria!r} em {args.falantes}')
        return 2
    sub.sort(key=lambda x: int(x['ordem']))
    sub = sub[:args.n]

    print(f'categoria={args.categoria}  {len(sub)} strings mostradas (de {args.n} pedidas)\n')
    print(f'{"ordem":>5} {"va_string":>12} {"ocorr":>5}  {"offsets-onde-aparece-como-ponteiro":<60} texto')
    achados = []
    for row in sub:
        va_txt = int(row['va_strings'].split(';')[0], 16)
        pat = struct.pack('<I', va_txt)
        offs = []
        p = 0
        while True:
            i = raw.find(pat, p)
            if i == -1:
                break
            offs.append(i)
            p = i + 1
        achados.append((int(row['ordem']), va_txt, offs, row['original'][:28]))
        offs_txt = ', '.join(f'0x{o:X}(va=0x{o+DELTA:08X})' for o in offs) if offs else '(nenhum — sondador ou string so referenciada indiretamente)'
        print(f'{row["ordem"]:>5} 0x{va_txt:08X} {row["ocorrencias"]:>5}  {offs_txt}')

    # tentativa automatica de stride: menor offset de cada ordem, diferenca entre ordens consecutivas
    print('\n-- diferencas entre o MENOR offset de ordens consecutivas --')
    menores = [(o, offs[0]) for o, va, offs, txt in achados if offs]
    for i in range(1, len(menores)):
        o0, off0 = menores[i - 1]
        o1, off1 = menores[i]
        print(f'  ordem {o0}->{o1}: offset 0x{off0:X} -> 0x{off1:X}  delta={off1 - off0} (0x{off1-off0:X})')

    return 0


if __name__ == '__main__':
    sys.exit(main())

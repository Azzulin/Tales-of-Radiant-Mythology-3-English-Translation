#!/usr/bin/env python3
"""Converte os `*_retorno.tsv` do P-68 no CSV que o `eboot_build2.py` consome.

Os lotes do P-68 guardam `va_ponteiros` (lista separada por `;`, porque a mesma
string pode ser apontada de varios lugares) e `bytes_jp`. O build quer uma linha
POR PONTEIRO, com `bloco`/`va_ponteiro`/`va_string`/`bytes_jp`/`traducao`.

Confere cada ponteiro contra o EBOOT antes de emitir: se o que esta la nao bate
com o `va_string` implicito, a linha nao entra — e' a guarda 1 do build, so' que
antes, com mensagem melhor.

Uso:
  p68_para_lote.py <eboot_dec> <glob_dos_retornos> <saida.csv>
"""
import sys, os, csv, json, glob, struct, collections

DELTA = 0x08803000


def main():
    eboot, padrao, saida = sys.argv[1], sys.argv[2], sys.argv[3]
    raw = open(eboot, 'rb').read()

    # os encurtamentos valem tambem para os blocos do P-68 (`arena`, `ui`, ...):
    # sem isto, o corte pedido no 3o turno nunca chega ao build (P-76).
    over = {}
    for cam in ('dados/item_equip_shrink/FINAL_encurtamentos.json',
                'dados/item_equip_correcoes.json'):
        if os.path.exists(cam):
            over.update(json.load(open(cam, encoding='utf-8')))
    usados = 0

    linhas, ruins = [], []
    porbloco = collections.Counter()
    for p in sorted(glob.glob(padrao)):
        for r in csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'):
            t = (r.get('traducao') or '').strip()
            if not t:
                continue
            if r['id'] in over:
                t = over[r['id']]
                usados += 1
            for vp in (r.get('va_ponteiros') or '').split(';'):
                vp = vp.strip()
                if not vp:
                    continue
                q = int(vp, 16)
                w, = struct.unpack_from('<I', raw, q - DELTA)
                # a string que esse ponteiro le tem de ser a do lote
                fim = raw.find(b'\x00', w - DELTA)
                jp = raw[w - DELTA:fim]
                if len(jp) != int(r['bytes_jp']):
                    ruins.append((r['id'], vp, len(jp), r['bytes_jp']))
                    continue
                linhas.append({'bloco': r['cena'], 'va_ponteiro': vp,
                               'va_string': f'0x{w:08X}',
                               'bytes_jp': len(jp), 'traducao': t,
                               'id': r['id'], 'original': r['original']})
                porbloco[r['cena']] += 1

    print(f'{usados} linhas sobrepostas por encurtamento')
    print(f'{len(linhas)} ponteiros em {len(porbloco)} blocos')
    for b, n in porbloco.most_common():
        print(f'   {b:<16}{n:>6}')
    if ruins:
        print(f'\n{len(ruins)} ponteiros DESCARTADOS (tamanho nao bate):')
        for i, vp, a, b in ruins[:8]:
            print(f'   [{i}] {vp}: EBOOT tem {a} B, lote diz {b} B')

    cols = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'id', 'original']
    with open(saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(linhas)
    print(f'\n-> {saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

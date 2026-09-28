#!/usr/bin/env python3
"""Inventario de strings do EBOOT descriptografado. Somente leitura.

Uso: eboot_texto.py <eboot_dec> <saida.csv> [--todas]

Le SOMENTE os primeiros `elf_size` bytes: o dump do PPSSPP tem cauda cifrada
depois do fim da tabela de secoes (ver P-41).
"""
import sys, csv, json, time
import prx, prx_texto

ELF_FIM = 5862704   # 0x597530


def main():
    src, saida = sys.argv[1], sys.argv[2]
    so_jp = '--todas' not in sys.argv
    d = open(src, 'rb').read()[:ELF_FIM]
    t0 = time.time()
    inv = prx_texto.inventario(d, min_len=2, so_japones=so_jp)
    dt = time.time() - t0
    itens = inv['itens']
    if not itens:
        print('ZERO strings — suspeitar do sondador, nao do jogo (P-39.5)')
        return 1
    cols = [c for c in itens[0].keys() if c != 'original'] + ['original', 'codificacao']
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in itens:
            r = dict(r)
            b = r['original']
            for enc in ('euc_jp', 'shift_jis'):
                try:
                    r['original'] = b.decode(enc)
                    r['codificacao'] = enc
                    break
                except UnicodeDecodeError:
                    continue
            else:
                r['original'] = b.hex()
                r['codificacao'] = 'hex'
            w.writerow(r)
    print(f'{len(itens)} strings em {dt:.1f}s -> {saida}')
    print(json.dumps(prx_texto.resumo(inv), indent=2, default=str, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())

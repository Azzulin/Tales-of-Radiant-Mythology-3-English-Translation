#!/usr/bin/env python3
"""Extrai o staff roll do EBOOT — texto sem ponteiro, em slots de 68 B (P-70).

As tres varreduras anteriores nao viram isto porque todas partiam do ponteiro:
`eboot_cobertura.py` junta os alvos de todo u32 do ELF e le a string em cada um.
O staff roll **nao e apontado por ninguem** — o codigo percorre a regiao em
passo fixo de 68 bytes. Texto que nao e alvo de ponteiro era um ponto cego do
metodo, e este e' o maior achado que ele escondia.

Estrutura, medida em 23/09/2026:

  regiao   0x08D1F888 .. ~0x08D2E028
  stride   68 B por entrada (deltas observados: 68, e multiplos para slot vazio)
  string   EUC-JP terminada em NUL, o resto do slot e' padding zero
  maior    46 B em japones -> sobra folga para o ingles

Uso:
  eboot_creditos_extrai.py <eboot_dec> <saida.tsv> [--ini 0x08D1F888] [--fim 0x08D2E100]
"""
import sys, csv, argparse

DELTA = 0x08803000
STRIDE = 68
NUL = b'\x00'


def eh_jp(s):
    n = i = 0
    while i < len(s) - 1:
        if 0xA1 <= s[i] <= 0xFE and 0xA1 <= s[i + 1] <= 0xFE:
            n += 1
            i += 2
        else:
            i += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('saida')
    ap.add_argument('--ini', default='0x08D1F888')
    ap.add_argument('--fim', default='0x08D2E100')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()
    ini, fim = int(args.ini, 16), int(args.fim, 16)

    linhas, vazios, naojp = [], 0, 0
    for k, va in enumerate(range(ini, fim, STRIDE)):
        p = va - DELTA
        slot = raw[p:p + STRIDE]
        z = slot.find(NUL)
        s = slot[:z] if z >= 0 else slot.rstrip(NUL)
        if not s or len(s) < 2:
            vazios += 1
            continue
        try:
            t = s.decode('euc_jp')
        except Exception:
            naojp += 1
            continue
        if eh_jp(s) == 0:                     # ja e ASCII: nada a traduzir
            naojp += 1
            continue
        # espaco REAL: do inicio do texto ate o proximo byte nao-zero. O stride
        # de 68 e' o caso comum, nao a regra — medir cada um (licao do P-67.14).
        q = p + len(s)
        while q < p + 400 and raw[q] == 0:
            q += 1
        espaco = q - p
        if espaco < len(s) + 4:               # sem folga: fora do bloco regular
            naojp += 1
            continue
        linhas.append([f'creditos#{k}', 'creditos', k, '(creditos)', '(credits)',
                       'sistema', '', t, '', '', f'0x{va:08X}', len(s), espaco - 1])

    with open(args.saida, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
                    'control_codes', 'original', 'traducao', 'nota_do_tradutor',
                    'va_string', 'bytes_jp', 'max_bytes'])
        w.writerows(linhas)
    print(f'{len(linhas)} entradas com japones  ({vazios} slots vazios, '
          f'{naojp} ja ASCII ou nao-EUC-JP)')
    print(f'maior string: {max((r[11] for r in linhas), default=0)} B '
          f'em slot de {STRIDE} B')
    print(f'-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

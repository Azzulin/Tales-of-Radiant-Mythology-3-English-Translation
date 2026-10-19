#!/usr/bin/env python3
"""Mede a cobertura de traducao de um EBOOT: quanto texto japones AINDA e'
apontado por algum ponteiro, e portanto o jogo ainda pode mostrar (P-68).

Toda frente do EBOOT ate' 22/09/2026 foi achada por screenshot — alguem jogou,
viu japones e a tabela foi cacada. Isso nunca e' exaustivo. Esta varredura e' a
conferencia que faltava, e e' barata: uma passada pelo ELF.

Japones solto no binario nao importa; se ninguem aponta pra ele, nunca aparece.
O que conta e' alvo de ponteiro.

Dois falsos positivos precisam de filtro, senao o numero infla quase o dobro:

  1. TABELA DE PONTEIRO. Todo VA deste binario acaba em 0x08, entao
     `XX XX AE 08` decodifica como dois pares EUC-JP validos. Por isso a string
     tem de ser japonesa DO COMECO AO FIM e sem byte de controle.
  2. `(verbatim)` DO PROPRIO BUILD (P-67.14). Ficou no pool novo, num endereco
     que nao e' o `va_string` do lote. Por isso o que ja' e' controlado se
     descobre resolvendo o ponteiro NO BINARIO CONSTRUIDO, nunca pelo lote.

Uso:
  eboot_cobertura.py <eboot> [--lotes CSV...] [--regioes] [--min-ptr N]

Rodar antes de chamar qualquer build de "definitivo": fora a regiao interna
(`初期化モジュール`, `本番メインループ` — nomes de modulo, nao texto de jogo), a
conta tem de ser zero.
"""
import sys, os, csv, struct, argparse, collections

DELTA = 0x08803000
ELF_FIM = 5862704

# Texto que NAO e alvo de ponteiro nao aparece aqui, por construcao — e o
# ponto cego desta ferramenta. Quem varre isso e' `eboot_orfas.py` (P-70).


# Mesma correcao do `bdi_cobertura.py` (P-80): par EUC-JP valido nao e' japones.
# Aqui o efeito e' menor porque `eh_jp` ja' exige a string INTEIRA em pares — o
# que entrava de errado era a string so' de simbolo de largura dupla
# (`β×Ψ＝√`), que nao e' texto traduzivel.
KANA_INI, KANA_FIM = 0x3040, 0x30FF
KANJI_INI, KANJI_FIM = 0x4E00, 0x9FFF
LARG_INI, LARG_FIM = 0xFF66, 0xFF9D


def eh_jp(s):
    """EUC-JP do comeco ao fim, sem byte de controle, E com kana ou kanji.

    Devolve nº de pares (0 se reprovar).
    """
    if not s or any(b < 0x20 for b in s):
        return 0
    n = i = 0
    while i < len(s) - 1:
        if 0xA1 <= s[i] <= 0xFE and 0xA1 <= s[i + 1] <= 0xFE:
            n += 1
            i += 2
        else:
            return 0
    if i < len(s) - 1:
        return 0
    t = s.decode('euc_jp', 'ignore')
    if not any(KANA_INI <= ord(c) <= KANA_FIM
               or KANJI_INI <= ord(c) <= KANJI_FIM
               or LARG_INI <= ord(c) <= LARG_FIM for c in t):
        return 0
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--lotes', nargs='*', default=[],
                    help='lotes do build; seus ponteiros sao resolvidos NO BINARIO '
                         'para descobrir o que ja e controlado (inclusive verbatim)')
    ap.add_argument('--regioes', action='store_true',
                    help='agrupa por regiao contigua em vez de listar string a string')
    ap.add_argument('--min-ptr', type=int, default=1)
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    controlados = set()
    for L in args.lotes:
        for r in csv.DictReader(open(L, encoding='utf-8')):
            vp = int(r['va_ponteiro'], 16)
            w, = struct.unpack_from('<I', raw, vp - DELTA)
            controlados.add(w)
    if args.lotes:
        print(f'{len(controlados)} alvos ja controlados pelos lotes\n')

    apont = collections.Counter()
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if DELTA <= w < DELTA + ELF_FIM:
            apont[w] += 1

    achados = []
    for va, n in apont.items():
        if n < args.min_ptr or va in controlados:
            continue
        p = va - DELTA
        fim = raw.find(b'\x00', p, p + 300)
        if fim == -1 or fim - p < 4:
            continue
        s = raw[p:fim]
        if eh_jp(s) >= 2:
            achados.append((va, n, s))
    achados.sort()

    tot = sum(len(s) for _, _, s in achados)
    print(f'texto japones ainda apontado e NAO controlado: '
          f'{len(achados)} strings, {tot} bytes')
    if not achados:
        print('COBERTURA COMPLETA.')
        return 0

    if args.regioes:
        reg, cur = [], [achados[0]]
        for a in achados[1:]:
            if a[0] - cur[-1][0] > 4096:
                reg.append(cur)
                cur = []
            cur.append(a)
        reg.append(cur)
        reg.sort(key=lambda r: -sum(len(s) for _, _, s in r))
        print(f'\n{len(reg)} regioes:\n')
        print(f'{"faixa":<26}{"str":>6}{"bytes":>7}  amostra')
        print('-' * 88)
        for r in reg:
            try:
                am = ' / '.join(s.decode('euc_jp')[:14] for _, _, s in r[:3])
            except Exception:
                am = '?'
            print(f'0x{r[0][0]:08X}..0x{r[-1][0]:08X}{len(r):>6}'
                  f'{sum(len(s) for _, _, s in r):>7}  {am[:44]}')
    else:
        for va, n, s in achados[:200]:
            try:
                t = s.decode('euc_jp')
            except Exception:
                continue
            print(f'  {n:>3}x  0x{va:08X}  {t[:50]}')
        if len(achados) > 200:
            print(f'  ... e mais {len(achados)-200}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Varre o EBOOT atras de japones que NENHUM ponteiro aponta (P-70).

`eboot_cobertura.py` parte do ponteiro: junta os alvos de todo u32 do ELF e le
a string em cada um. Bom metodo, mas com um ponto cego — texto que o codigo
percorre em passo fixo, sem tabela de ponteiro, nao e' alvo de ninguem e
portanto nunca aparece la. Foi assim que o staff roll do jogo (659 entradas)
ficou escondido de tres varreduras seguidas.

Dois filtros, sem os quais o resultado nao presta:

  1. Descarta o que e' alvo de ponteiro (esse e' trabalho da outra ferramenta).
  2. Descarta FRAGMENTO: um run de kana no meio de uma string ja apontada nao e'
     texto novo, e' o miolo de algo que ja tem dono.

Uso:
  eboot_orfas.py <eboot_dec> [--todas] [--saida CSV]

Sem `--todas`, o que ja' foi decidido como fora de escopo (P-70.2) e' contado a
parte, para nao voltar a parecer lacuna nova a cada auditoria.
"""
import sys, re, struct, bisect, argparse, csv, collections

DELTA = 0x08803000
ELF_FIM = 5862704
NUL = b'\x00'
EU = re.compile(rb'(?:\xa4[\xa1-\xf3]|\xa5[\xa1-\xf6]){3,}')

# Achado, medido e DELIBERADAMENTE nao traduzido — ver P-70.2 e
# `lotes_bancos/fora_de_escopo/LEIA-ME.md`. Continua em japones de proposito.
FORA_DE_ESCOPO = [
    (0x08D1F888, 0x08D2E138, 'staff roll (creditos) — decisao de 23/09/2026'),
    # prompts soltos e de depuracao, mesma decisao (lote `ORFAS`)
    (0x08CE0B00, 0x08CE0B20, 'prompt/depuracao — decisao de 23/09/2026'),
    (0x08CE7600, 0x08CE7740, 'prompt/depuracao — decisao de 23/09/2026'),
    (0x08CEA9F0, 0x08CEAA40, 'prompt/depuracao — decisao de 23/09/2026'),
    (0x08CFE010, 0x08CFE040, 'prompt/depuracao — decisao de 23/09/2026'),
    (0x08D03A80, 0x08D03AC0, 'prompt/depuracao — decisao de 23/09/2026'),
]


def jp_puro(s):
    if not s or any(b < 0x20 for b in s):
        return 0
    n = i = 0
    while i < len(s) - 1:
        if 0xA1 <= s[i] <= 0xFE and 0xA1 <= s[i + 1] <= 0xFE:
            n += 1
            i += 2
        else:
            return 0
    return n if i >= len(s) - 1 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--todas', action='store_true',
                    help='inclui tambem as regioes ja decididas como fora de escopo')
    ap.add_argument('--saida', default='')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()[:ELF_FIM]

    apont = set()
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if DELTA <= w < DELTA + ELF_FIM:
            apont.add(w)

    span = []
    for va in apont:
        p = va - DELTA
        f = raw.find(NUL, p, p + 400)
        if f > p:
            span.append((va, va + (f - p)))
    span.sort()
    ini = [a for a, _ in span]

    def fragmento(va):
        i = bisect.bisect_right(ini, va) - 1
        return i >= 0 and span[i][0] < va < span[i][1]

    orfas, fora, frag = {}, collections.Counter(), 0
    for m in EU.finditer(raw):
        i = raw.rfind(NUL, max(0, m.start() - 120), m.start())
        i = i + 1 if i >= 0 else m.start()
        j = raw.find(NUL, m.end(), m.end() + 120)
        j = j if j >= 0 else m.end()
        va = i + DELTA
        if jp_puro(raw[i:j]) < 2 or va in apont:
            continue
        if fragmento(va):
            frag += 1
            continue
        rot = next((r for a, b, r in FORA_DE_ESCOPO if a <= va < b), None)
        if rot and not args.todas:
            fora[rot] += 1
            continue
        orfas.setdefault(va, raw[i:j])

    print(f'{frag} fragmentos dentro de string ja apontada (nao sao texto novo)')
    for rot, n in fora.items():
        print(f'{n} strings em regiao FORA DE ESCOPO, nao contadas: {rot}')
    print(f'\njapones orfao (nenhum ponteiro aponta): {len(orfas)} strings')
    if not orfas:
        print('NENHUM. O ponto cego esta coberto.')
        return 0

    reg, itens = [], sorted(orfas.items())
    cur = [itens[0]]
    for a in itens[1:]:
        if a[0] - cur[-1][0] > 2048:
            reg.append(cur)
            cur = []
        cur.append(a)
    reg.append(cur)
    reg.sort(key=lambda r: -len(r))
    print(f'\n{len(reg)} regioes:\n')
    for r in reg:
        try:
            am = ' / '.join(s.decode('euc_jp')[:14] for _, s in r[:3])
        except Exception:
            am = '?'
        print(f'  0x{r[0][0]:08X}..0x{r[-1][0]:08X}  {len(r):>4} strings  {am[:46]}')

    if args.saida:
        with open(args.saida, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['va_string', 'bytes_jp', 'original'])
            for va, s in itens:
                w.writerow([f'0x{va:08X}', len(s), s.decode('euc_jp', 'replace')])
        print(f'\n-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

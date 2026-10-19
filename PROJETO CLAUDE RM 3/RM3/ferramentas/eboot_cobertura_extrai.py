#!/usr/bin/env python3
"""Extrai o texto japones que a varredura de cobertura (P-68) achou sem dono, e
monta os lotes de traducao no formato `SIS-NN.tsv`.

Recebe o mesmo par que o `eboot_cobertura.py` (EBOOT + todos os lotes do build),
acha o que ainda e' apontado e nao e' controlado, agrupa em blocos por regiao
contigua, e escreve um `.tsv` por lote com as colunas que o `valida_retorno.py`
ja' conhece — mais `va_ponteiros`/`ocorrencias`, como os `SIS-NN`.

Calcula tambem o ORCAMENTO DE BYTES de cada bloco, pelo criterio seguro do
P-67.14: espaco e' so' onde as strings do bloco ja' moram, nunca o buraco entre
ponteiros (la' vivem os campos do registro). Sem esse numero no briefing, a
traducao volta sem caber — foi o que aconteceu com `valuables`.

Uso:
  eboot_cobertura_extrai.py <eboot> --lotes <csv...> --saida <dir>
                            [--mapa NOME=0xINI[,0xINI...]] [--excluir 0xINI]
"""
import sys, os, csv, struct, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from item_equip_segmenta_arena import segmentos_livres

DELTA = 0x08803000
ELF_FIM = 5862704


def eh_jp(s):
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


COLS = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
        'control_codes', 'original', 'traducao', 'nota_do_tradutor',
        'va_ponteiros', 'ocorrencias', 'bytes_jp', 'max_bytes']


def orcamento(r, espaco):
    """Quantos bytes ASCII cada fala pode gastar, para o bloco inteiro caber.

    Reparte o espaco em proporcao ao tamanho do japones (fala longa merece mais
    que fala curta), com piso de 4 B. Sem isso o tradutor traduz no escuro e o
    lote volta sem caber — foi o que aconteceu com `valuables` (P-67.14).
    """
    # dedup por texto, como o pool do build faz
    unico = {}
    for va, ps, s in r:
        unico.setdefault(s, len(s))
    jp = sum(n + 1 for n in unico.values())
    fator = (espaco / jp) if jp else 1.0
    return {s: max(4, int((n + 1) * fator) - 1) for s, n in unico.items()}


def escreve_lotes(saida, rotulo, blocos, teto, orcs=None):
    """Escreve `<rotulo>-NN.tsv` (ou `<rotulo>.tsv` se couber num so)."""
    linhas = []
    for bloco, r in blocos:
        orc = (orcs or {}).get(bloco, {})
        for i, (va, ps, s) in enumerate(r):
            try:
                t = s.decode('euc_jp')
            except Exception:
                continue
            linhas.append([f'{bloco}#{i}', bloco, i, '(sistema)', '(system)',
                           'sistema', '', t, '', '',
                           ';'.join(f'0x{q:08X}' for q in ps), len(ps), len(s),
                           orc.get(s, '')])
    partes = [linhas[i:i + teto] for i in range(0, len(linhas), teto)] or [[]]
    for k, parte in enumerate(partes, 1):
        nome = f'{rotulo}-{k:02d}' if len(partes) > 1 else rotulo
        cam = os.path.join(saida, f'{nome}.tsv')
        with open(cam, 'w', newline='', encoding='utf-8') as fh:
            w = csv.writer(fh, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            w.writerow(COLS)
            w.writerows(parte)
        print(f'-> {cam}  {len(parte)} falas')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--lotes', nargs='*', default=[])
    ap.add_argument('--saida', required=True)
    ap.add_argument('--mapa', action='append', default=[],
                    help='NOME=0xINI — batiza a regiao que comeca nesse endereco')
    ap.add_argument('--excluir', action='append', default=[],
                    help='0xINI de regiao a NAO extrair (texto interno)')
    ap.add_argument('--teto', type=int, default=320, help='falas por lote')
    ap.add_argument('--misc', metavar='ROTULO',
                    help='junta num lote so os blocos com menos de --misc-max falas')
    ap.add_argument('--misc-max', type=int, default=60)
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()
    nomes = {}
    for m in args.mapa:
        n, v = m.split('=')
        nomes[int(v, 16)] = n
    excl = {int(v, 16) for v in args.excluir}

    controlados = set()
    for L in args.lotes:
        for r in csv.DictReader(open(L, encoding='utf-8')):
            w, = struct.unpack_from('<I', raw, int(r['va_ponteiro'], 16) - DELTA)
            controlados.add(w)

    # alvo -> lista de ponteiros. `todos_ptrs` guarda o ENDERECO de cada
    # ponteiro: e o que o orcamento precisa, porque ponteiro dentro da faixa
    # nao e espaco (P-67.12/67.14).
    ptr_de = collections.defaultdict(list)
    todos_ptrs = set()
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        if DELTA <= w < DELTA + ELF_FIM:
            ptr_de[w].append(q + DELTA)
            todos_ptrs.add(q + DELTA)

    ach = []
    for va, ps in ptr_de.items():
        if va in controlados:
            continue
        p = va - DELTA
        f = raw.find(b'\x00', p, p + 300)
        if f == -1 or f - p < 4:
            continue
        s = raw[p:f]
        if eh_jp(s) >= 2:
            ach.append((va, ps, s))
    ach.sort()

    reg, cur = [], [ach[0]]
    for a in ach[1:]:
        if a[0] - cur[-1][0] > 4096:
            reg.append(cur)
            cur = []
        cur.append(a)
    reg.append(cur)

    os.makedirs(args.saida, exist_ok=True)
    manifesto = []
    miscelanea = []
    for r in reg:
        ini = r[0][0]
        if ini in excl:
            print(f'pulada (interna): 0x{ini:08X}  {len(r)} strings')
            continue
        bloco = nomes.get(ini, f'bloco_{ini:08X}')
        if args.misc and len(r) < args.misc_max:
            miscelanea.append((bloco, r))
            continue

        # orcamento: espaco = do inicio da 1a string ao fim da ultima, MENOS o
        # que ponteiro ocupa la dentro (P-67.14). Aqui nao ha ponteiro no meio,
        # mas medimos assim mesmo para o numero ser o real.
        a0 = min(va for va, _, _ in r)
        a1 = max(va + len(s) + 1 for va, _, s in r)
        dentro = sorted(q for q in ptr_de
                        for _ in [0] if a0 <= q < a1)
        ocupado_ptr = 0
        marcados = set()
        for _, ps, _ in r:
            for q in ps:
                if a0 <= q < a1 and q not in marcados:
                    marcados.add(q)
                    ocupado_ptr += 4
        jp_total = sum(len(s) + 1 for _, _, s in r)
        # espaco SEGURO (P-67.14): so onde as strings ja moram, sem ponteiro
        strs = {(va, len(s)) for va, _, s in r}
        esp = sum(y - x for x, y in segmentos_livres(a0, a1, todos_ptrs, strs))
        manifesto.append((bloco, len(r), jp_total, a0, a1, esp))

        escreve_lotes(args.saida, bloco.upper(), [(bloco, r)], args.teto,
                      {bloco: orcamento(r, esp)})

    if miscelanea:
        n = sum(len(r) for _, r in miscelanea)
        a0 = min(va for _, r in miscelanea for va, _, _ in r)
        a1 = max(va + len(s) + 1 for _, r in miscelanea for va, _, s in r)
        jp = sum(len(s) + 1 for _, r in miscelanea for _, _, s in r)
        # cada sub-bloco do misc tem a sua propria faixa e o seu orcamento
        orcs, esp_tot = {}, 0
        for b, sub in miscelanea:
            x0 = min(va for va, _, _ in sub)
            x1 = max(va + len(s) + 1 for va, _, s in sub)
            strs = {(va, len(s)) for va, _, s in sub}
            e = sum(y - x for x, y in segmentos_livres(x0, x1, todos_ptrs, strs))
            orcs[b] = orcamento(sub, e)
            esp_tot += e
        manifesto.append((args.misc + ' (' + ', '.join(b for b, _ in miscelanea) + ')',
                          n, jp, a0, a1, esp_tot))
        escreve_lotes(args.saida, args.misc.upper(), miscelanea, args.teto, orcs)

    print(f'\n{"bloco":<20}{"falas":>7}{"bytes JP":>10}{"arena":>9}  faixa')
    print('-' * 74)
    for b, n, jp, a0, a1, tam in sorted(manifesto, key=lambda x: -x[1]):
        print(f'{b:<20}{n:>7}{jp:>10}{tam:>9}  0x{a0:08X}..0x{a1:08X}')
    cam = os.path.join(args.saida, '00_MANIFESTO.csv')
    with open(cam, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['bloco', 'falas', 'bytes_jp_total', 'arena_bytes',
                    'va_ini', 'va_fim'])
        for b, n, jp, a0, a1, tam in manifesto:
            w.writerow([b, n, jp, tam, f'0x{a0:08X}', f'0x{a1:08X}'])
    print(f'\n-> {cam}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

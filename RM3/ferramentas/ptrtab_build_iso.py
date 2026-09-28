#!/usr/bin/env python3
"""Gera a ISO com o nome COMPLETO de personagem traduzido (PTRTAB, P-25/P-57).

Uso:
  py ptrtab_build_iso.py <iso_in> <entrada_v> <ficha_nomes.csv> <iso_out> [--aplicar] [--forcar]

`entrada_v` e' a entrada do bdi que contem o EZBIND ANINHADO com os tres
arquivos `CharGuideText{CName,ORG,TOW3}.bin` dentro (3082 no levantamento
atual, P-25) — cada um guardado CRU dentro desse EZBIND, sem gzip (diferente
de `.scr`/`.txz`). So' `CName` (nomes completos) e' reescrito; `ORG`/`TOW3`
(biografia, fora de escopo) ficam intocados.

Mesma politica de seguranca de `bdi_build_iso.py`/`txz_build_iso.py`: nunca
escreve na ISO original, so' escreve dentro do span que a entrada ja ocupa
(usa o mesmo par buraco-in-place / remonta-do-EZBIND), rele a ISO gerada e
confere string por string, e reporta qualquer setor escrito fora do plano.
"""
import sys, os, csv, struct, collections
import ptrtab
from bdi_build_iso import ezbind_parse, buraco_de, alinhamento, ezbind_remonta, SEC

NOME_ARQUIVO = 'CharGuideTextCName.bin'


def carrega_traducoes(csv_nomes):
    trad = {}
    for r in csv.DictReader(open(csv_nomes, encoding='utf-8-sig')):
        t = r['traducao'].strip()
        if t:
            trad[int(r['id'].split(':')[1])] = t
    return trad


def main():
    import shutil, time
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    iso_in, entrada_v, csv_nomes, iso_out = (sys.argv[1], int(sys.argv[2]),
                                              sys.argv[3], sys.argv[4])
    aplicar = '--aplicar' in sys.argv
    forcar = '--forcar' in sys.argv

    if os.path.abspath(iso_in) == os.path.abspath(iso_out):
        print('RECUSADO: a saida e a mesma ISO da entrada. Trabalhe em copia.')
        return 1
    if aplicar and os.path.exists(iso_out) and not forcar:
        print(f'RECUSADO: {iso_out} ja existe. Apague, ou use --forcar.')
        return 1

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bdi import load_index

    trad = carrega_traducoes(csv_nomes)
    print(f'{len(trad)} nomes completos traduzidos (de {94})')
    if not trad:
        print('nada a fazer')
        return 1

    base = 106896 * SEC
    with open(iso_in, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        e = pore.get(entrada_v)
        if not e:
            print(f'RECUSADO: entrada {entrada_v} nao existe no bdi')
            return 1
        f.seek(base + e['off'])
        blob = f.read(e['span'])

    pe = ezbind_parse(blob)
    if not pe:
        print('RECUSADO: entrada nao e EZBIND')
        return 1
    count, cab_do, regs = pe
    alin = alinhamento(regs)
    alvo = next(((i, r) for i, r in enumerate(regs) if r[0] == NOME_ARQUIVO), None)
    if not alvo:
        print(f'RECUSADO: {NOME_ARQUIVO} nao encontrado dentro da entrada {entrada_v}')
        return 1
    i, (nome, no, sz, do, key) = alvo
    raw = blob[do:do + sz]
    p = ptrtab.parse(raw)
    if ptrtab.build(p) != raw:
        print('RECUSADO: round-trip do PTRTAB original falhou')
        return 1
    if p['count'] != 94:
        print(f'RECUSADO: esperava 94 strings, achei {p["count"]}')
        return 1

    novas = []
    for idx, s in enumerate(p['strings']):
        if idx in trad:
            novas.append(trad[idx].encode('euc_jp'))
        else:
            novas.append(s)
    p2 = dict(p); p2['strings'] = novas
    novo_raw = ptrtab.build(p2)
    if ptrtab.parse(novo_raw)['strings'] != novas:
        print('RECUSADO: round-trip do PTRTAB novo falhou')
        return 1

    buraco = buraco_de(regs, i, len(blob))
    print(f'PTRTAB novo: {len(novo_raw)} B, slot original {sz} B, buraco disponivel {buraco} B')
    if len(novo_raw) <= buraco:
        novo_blob = bytearray(blob)
        novo_blob[do:do + len(novo_raw)] = novo_raw
        for q in range(do + len(novo_raw), do + buraco):
            novo_blob[q] = 0
        struct.pack_into('<I', novo_blob, 0x10 + i * 16 + 4, len(novo_raw))
        novo_blob = bytes(novo_blob)
        modo = 'in-place (buraco)'
    else:
        cand = ezbind_remonta(blob, regs, i, novo_raw, alin)
        if len(cand) > e['span']:
            print(f'RECUSADO: remontagem do EZBIND estoura o span em {len(cand)-e["span"]} B')
            return 1
        novo_blob = cand + b'\x00' * (e['span'] - len(cand))
        modo = 'remontagem do EZBIND'
    print(f'modo: {modo}')

    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    t0 = time.time()
    print(f'\ncopiando a ISO ({os.path.getsize(iso_in)/2**30:.2f} GB)...', flush=True)
    shutil.copyfile(iso_in, iso_out)
    print(f'  copiada em {time.time()-t0:.0f}s')
    assert os.path.getsize(iso_out) == os.path.getsize(iso_in), 'tamanho mudou na copia'

    off = base + e['off']
    with open(iso_out, 'r+b') as g:
        g.seek(off); g.write(novo_blob)
        g.flush(); os.fsync(g.fileno())

    print('\nconferindo, relendo a ISO gerada...')
    with open(iso_out, 'rb') as g:
        g.seek(off)
        lido = g.read(e['span'])
    ok = lido == novo_blob
    print(f'  entrada bate com o planejado? {ok}')
    regs2 = ezbind_parse(lido)[2]
    d2 = [r2 for r2 in regs2 if r2[0] == NOME_ARQUIVO][0]
    raw2 = lido[d2[3]:d2[3] + d2[2]]
    strs2 = ptrtab.parse(raw2)['strings']
    conferido = strs2 == novas
    print(f'  as 94 strings batem com o planejado? {conferido}')

    print('\ndiff por setor contra a entrada...')
    setores = set()
    with open(iso_in, 'rb') as a, open(iso_out, 'rb') as b:
        a.seek(off - (off % SEC)); b.seek(off - (off % SEC))
        pos = off - (off % SEC)
        rng = e['span'] + (off % SEC) + SEC
        x = a.read(rng); y = b.read(rng)
        for k in range(0, len(x), SEC):
            if x[k:k+SEC] != y[k:k+SEC]:
                setores.add((pos + k) // SEC)
    dentro = set(range(e['off'] // SEC + base // SEC, (e['off'] + e['span']) // SEC + base // SEC + 1))
    fora = setores - dentro
    print(f'  setores diferentes: {len(setores)} | fora do esperado: {len(fora)}')
    print(f'\n-> {iso_out}')
    return 0 if (ok and conferido) else 1


if __name__ == '__main__':
    sys.exit(main())

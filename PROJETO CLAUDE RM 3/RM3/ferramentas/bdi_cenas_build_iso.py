#!/usr/bin/env python3
"""Reinsere cenas `.scr` AVULSAS numa ISO que ja' esta montada (P-73.1).

`bdi_build_iso.py` reconstroi o dialogo inteiro a partir da ISO ORIGINAL, o que
e' certo quando a leva e' grande — mas desfaz tudo o que ja' foi aplicado por
cima (EBOOT, `.txz`, PTRTAB, bancos). Para umas poucas cenas que nunca tinham
sido traduzidas, como as 65 do `CAMPO-02` (P-68.1), refazer a ISO do zero seria
caro e arriscado.

Esta ferramenta e' cirurgica: escreve SO' as cenas que o lote nomeia, dentro do
span que a entrada do bdi ja ocupa, e nao toca em mais nada. Mesma politica das
outras: recusa escrever na original, recomprime preservando o cabecalho gzip
byte a byte, e **rele a ISO gerada** conferindo string por string.

O lote so' precisa de `cena` (nome do `.scr`), `ordem` (indice da string dentro
dele) e `traducao`.

Uso:
  bdi_cenas_build_iso.py <iso_in> <iso_out> <catalogo.csv> <lote.tsv>... [--aplicar]
"""
import sys, os, csv, gzip, glob, struct, shutil, time, collections, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import (ezbind_parse, buraco_de, alinhamento, ezbind_remonta,
                           fc_parse, fc_build, gzip_como_original)

SEC = 2048
LBA = 106896
NUL = b'\x00'
ENC = 'euc_jp'


def carrega(padroes):
    """{cena_minuscula: {indice_da_string: traducao}}"""
    m = collections.defaultdict(dict)
    for pat in padroes:
        for p in sorted(glob.glob(pat)):
            with open(p, encoding='utf-8') as f:
                for r in csv.DictReader(f, delimiter='\t'):
                    t = (r.get('traducao') or '').strip()
                    if t:
                        m[r['cena'].lower()][int(r['ordem'])] = t
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('catalogo')
    ap.add_argument('lotes', nargs='+')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    if os.path.abspath(args.iso_in) == os.path.abspath(args.iso_out):
        print('RECUSADO: entrada e saida sao a mesma ISO')
        return 1
    if 'Caravan.iso' in os.path.basename(args.iso_out):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1

    trad = carrega(args.lotes)
    print('%d cenas com traducao, %d falas'
          % (len(trad), sum(len(v) for v in trad.values())))

    porv = collections.defaultdict(set)
    with open(args.catalogo, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            n = r['nome'].lower()
            if n.endswith('.scr') and n in trad:
                porv[int(r['entrada_v'])].add(n)
    alvos = sum(len(v) for v in porv.values())
    print('cenas achadas no catalogo: %d em %d entradas do bdi\n' % (alvos, len(porv)))
    if not alvos:
        print('nenhuma cena do lote casou com o catalogo')
        return 1

    base = LBA * SEC
    plano, pulados, conf = [], [], []
    with open(args.iso_in, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        for v in sorted(porv):
            e = pore.get(v)
            if not e:
                for nm in porv[v]:
                    pulados.append((nm, 'entrada do bdi ausente'))
                continue
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            pe = ezbind_parse(blob)
            if not pe:
                for nm in porv[v]:
                    pulados.append((nm, 'entrada nao e EZBIND'))
                continue
            count, cab_do, regs = pe
            alin = alinhamento(regs)
            novo_blob = blob
            mudou = False
            for i, (nome, no, sz, do, key) in enumerate(regs):
                ln = nome.lower()
                if ln not in porv[v]:
                    continue
                raw = novo_blob[do:do + sz]
                try:
                    scr = gzip.decompress(raw)
                    p = fc_parse(scr)
                except Exception as ex:
                    pulados.append((nome, '%s: %s' % (type(ex).__name__, ex)))
                    continue
                if fc_build(p, p['strings']) != scr:
                    pulados.append((nome, 'round-trip do FaceChat original falhou'))
                    continue
                novas = list(p['strings'])
                n = 0
                for idx, t in trad[ln].items():
                    if 0 <= idx < len(novas):
                        novas[idx] = t.encode(ENC, 'replace')
                        n += 1
                if not n:
                    continue
                novo_scr = fc_build(p, novas)
                if fc_parse(novo_scr)['strings'] != novas:
                    pulados.append((nome, 'round-trip do FaceChat novo falhou'))
                    continue
                novo_gz = gzip_como_original(novo_scr, raw)
                buraco = buraco_de(regs, i, len(novo_blob))
                if len(novo_gz) <= buraco:
                    nb = bytearray(novo_blob)
                    nb[do:do + len(novo_gz)] = novo_gz
                    for q in range(do + len(novo_gz), do + buraco):
                        nb[q] = 0
                    struct.pack_into('<I', nb, 0x10 + i * 16 + 4, len(novo_gz))
                    novo_blob = bytes(nb)
                else:
                    cand = ezbind_remonta(novo_blob, regs, i, novo_gz, alin)
                    if len(cand) > e['span']:
                        pulados.append((nome, 'nao cabe no span (%d B a mais)'
                                        % (len(cand) - e['span'])))
                        continue
                    novo_blob = cand + NUL * (e['span'] - len(cand))
                _, _, regs = ezbind_parse(novo_blob)
                mudou = True
                conf.append((v, nome, novas))
            if mudou:
                plano.append((base + e['off'], novo_blob, e['span']))

    print('cenas a escrever: %d' % len(conf))
    if pulados:
        print('%d cenas PULADAS (o japones delas fica intacto):' % len(pulados))
        for nm, m in pulados[:10]:
            print('   %s: %s' % (nm, m))
    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    if not plano:
        print('nada a escrever')
        return 1

    if not os.path.exists(args.iso_out):
        t0 = time.time()
        print('\ncopiando a ISO (%.2f GB)...'
              % (os.path.getsize(args.iso_in) / 2 ** 30), flush=True)
        shutil.copyfile(args.iso_in, args.iso_out)
        print('  copiada em %.0fs' % (time.time() - t0))
    if os.path.getsize(args.iso_out) != os.path.getsize(args.iso_in):
        print('RECUSADO: a saida mudou de tamanho')
        return 1

    with open(args.iso_out, 'r+b') as g:
        for off, dados, span in plano:
            g.seek(off)
            g.write(dados)
        g.flush()
        os.fsync(g.fileno())

    print('\nconferindo, relendo a ISO gerada...')
    ok = ruim = 0
    with open(args.iso_out, 'rb') as g:
        _, _, entries, _ = load_index(g, base)
        pore = {e['v']: e for e in entries}
        for v, nome, esperado in conf:
            e = pore[v]
            g.seek(base + e['off'])
            blob = g.read(e['span'])
            _, _, regs = ezbind_parse(blob)
            alvo = None
            for (nm, no, sz, do, key) in regs:
                if nm.lower() == nome.lower():
                    alvo = (sz, do)
                    break
            if not alvo:
                ruim += 1
                continue
            sz, do = alvo
            p = fc_parse(gzip.decompress(blob[do:do + sz]))
            if p['strings'] == esperado:
                ok += 1
            else:
                ruim += 1
                print('   DIVERGE: %s' % nome)
    print('releitura: %d cenas conferidas, %d divergentes' % (ok, ruim))
    if ruim:
        return 1
    print('-> %s' % args.iso_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

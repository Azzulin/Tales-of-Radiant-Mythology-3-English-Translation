#!/usr/bin/env python3
"""Reinsere strings IN-PLACE num arquivo do `namco.bdi`, por offset (P-73.2).

Para formato que nao foi decifrado e portanto nao tem `parse`/`build`. O caso
que motivou: `cJudas_Majinrengokusatsu_0.zqe`, a encantacao de Mystic Arte do
Judas (P-68.3) — sabe-se onde cada fala mora e que ha folga depois dela, mas
nao o que sao os bytes em volta.

A regra e' conservadora por isso: escreve a traducao no MESMO offset, termina
com NUL e zera o resto ate o proximo byte nao-nulo. **Nao move nada e nao
recalcula nada** — se o formato tiver um campo de tamanho em algum lugar que
nao conhecemos, ele continua valendo, porque o espaco ocupado nao passa do que
ja estava reservado.

RECUSA qualquer fala que nao caiba no espaco medido. Meio arquivo escrito e'
pior que nenhum.

O lote precisa de `offset_arquivo`, `bytes_jp` e `traducao`.

Uso:
  bdi_inplace_build_iso.py <iso_in> <iso_out> <entrada_v> <arquivo> <lote.tsv>
                           [--aplicar]
"""
import sys, os, csv, gzip, struct, shutil, time, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse
from bdi_varre_texto import arquivos

SEC = 2048
LBA = 106896
NUL = b'\x00'


def localiza(blob, alvo, prof=0, base=0):
    """(offset_absoluto_no_blob, tamanho) do arquivo, se ele estiver CRU.

    So' serve para conteudo nao comprimido: se o arquivo estiver dentro de um
    gzip, o offset no blob nao existe e a escrita in-place nao se aplica.
    """
    pe = ezbind_parse(blob)
    if not pe:
        return None
    _, _, regs = pe
    for nome, no, sz, do, key in regs:
        sub = blob[do:do + sz]
        if nome.lower() == alvo.lower():
            if sub[:3] == b'\x1f\x8b\x08':
                return None                      # comprimido: nao da in-place
            return (base + do, sz)
        if sub[:6] == b'EZBIND':
            r = localiza(sub, alvo, prof + 1, base + do)
            if r:
                return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('entrada_v', type=int)
    ap.add_argument('arquivo')
    ap.add_argument('lote')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    if os.path.abspath(args.iso_in) == os.path.abspath(args.iso_out):
        print('RECUSADO: entrada e saida sao a mesma ISO')
        return 1
    if 'Caravan.iso' in os.path.basename(args.iso_out):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1

    with open(args.lote, encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(f, delimiter='\t')
                if (r.get('traducao') or '').strip()]
    print('%d falas no lote' % len(rows))

    base = LBA * SEC
    with open(args.iso_in, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        e = {x['v']: x for x in entries}.get(args.entrada_v)
        if not e:
            print('RECUSADO: entrada %d nao existe' % args.entrada_v)
            return 1
        f.seek(base + e['off'])
        blob = f.read(e['span'])

    loc = localiza(blob, args.arquivo)
    if not loc:
        print('RECUSADO: %s nao esta CRU dentro da entrada %d '
              '(ausente ou comprimido)' % (args.arquivo, args.entrada_v))
        return 1
    off_arq, sz = loc
    sub = blob[off_arq:off_arq + sz]
    print('%s: %d B, offset %d dentro da entrada' % (args.arquivo, sz, off_arq))

    edicoes = []
    for r in rows:
        o = int(r['offset_arquivo'])
        n = int(r['bytes_jp'])
        q = o + n
        while q < len(sub) and sub[q] == 0:
            q += 1
        espaco = q - o
        en = r['traducao'].encode('ascii', 'replace')
        if len(en) + 1 > espaco:
            print('RECUSADO: [%s] %d B + NUL nao cabe nos %d B de %d'
                  % (r['id'], len(en), espaco, o))
            return 1
        edicoes.append((o, en, espaco))
        print('   off %-6d %2d B -> %-26r (espaco %d)'
              % (o, len(en), r['traducao'][:24], espaco))

    novo_sub = bytearray(sub)
    for o, en, espaco in edicoes:
        novo_sub[o:o + espaco] = en + NUL * (espaco - len(en))
    novo_blob = bytearray(blob)
    novo_blob[off_arq:off_arq + sz] = bytes(novo_sub)
    novo_blob = bytes(novo_blob)
    if len(novo_blob) != len(blob):
        print('RECUSADO: o blob mudou de tamanho')
        return 1

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

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
        g.seek(base + e['off'])
        g.write(novo_blob)
        g.flush()
        os.fsync(g.fileno())

    print('\nconferindo, relendo a ISO gerada...')
    with open(args.iso_out, 'rb') as g:
        g.seek(base + e['off'])
        lido = g.read(e['span'])
    if lido != novo_blob:
        print('RECUSADO: a releitura do blob nao bate')
        return 1
    conf = lido[off_arq:off_arq + sz]
    ok = 0
    for r in rows:
        o = int(r['offset_arquivo'])
        z = conf.find(NUL, o)
        if conf[o:z].decode('ascii', 'replace') == r['traducao']:
            ok += 1
        else:
            print('   DIVERGE em %d: %r' % (o, conf[o:z][:30]))
    print('releitura: %d de %d falas conferidas' % (ok, len(rows)))
    if ok != len(rows):
        return 1
    print('-> %s' % args.iso_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

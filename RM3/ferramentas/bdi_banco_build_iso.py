#!/usr/bin/env python3
"""Reinsere no `namco.bdi` os bancos que nao tinham ferramenta de build (P-73).

Fecha a lacuna do P-69: `campofixo.py`, `oldata.py` e `ptrtab.py` sempre tiveram
`build()`, mas ninguem tinha escrito o passo que pega o resultado e o escreve
dentro da ISO. Sao tres formatos e tres formas de guardar:

  campofixo  v2063  titulos de skit       arquivo CRU, campo fixo de 64 B
  oldata     v2069  sinopse               arquivo CRU, cabecalho u16
  oldata     v2070  titulos de capitulo   arquivo GZIP, cabecalho u32
  ptrtab     v3082  perfis ORG/TOW3       dentro de um EZBIND, sem gzip

Mesma politica de seguranca das outras tres ferramentas de ISO: nunca escreve
na original, so' dentro do span que a entrada ja ocupa, faz round-trip antes e
depois, e **rele a ISO gerada** conferindo registro por registro.

O casamento com o lote e' por TEXTO, nunca por indice: as tabelas de extracao
filtraram linha vazia, entao `ordem` nao alinha com a posicao real no banco —
isso custou uma rodada no P-71.

Uso:
  bdi_banco_build_iso.py <iso_in> <iso_out> <formato> <entrada_v> <lote.tsv>...
                         [--arquivo NOME] [--aplicar]
"""
import sys, os, csv, gzip, zlib, struct, shutil, time, glob, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import (ezbind_parse, buraco_de, alinhamento, ezbind_remonta,
                           gzip_como_original)
import campofixo, oldata, ptrtab

SEC = 2048
LBA = 106896
NUL = b'\x00'
GZ_MAGIC = b'\x1f\x8b\x08'
ENC = 'euc_jp'


def carrega_lote(padroes):
    """{japones_como_o_extrator_gravou: ingles}"""
    m = {}
    for pat in padroes:
        for p in sorted(glob.glob(pat)):
            with open(p, encoding='utf-8') as f:
                for r in csv.DictReader(f, delimiter='\t'):
                    t = (r.get('traducao') or '').strip()
                    if t:
                        m[r['original']] = t
    return m


def chave(b):
    """Mesma decodificacao que o extrator usou — inclusive o U+FFFD de byte que
    ele nao soube ler (o codigo de cor da sinopse, P-71). Usar outra chave aqui
    faz o casamento falhar em 100% das linhas afetadas."""
    return b.decode(ENC, 'replace')


def _enc(t):
    """EUC-JP, deixando passar byte cru < 0x100.

    `sinopse_restaura_cor.py` devolve os codigos de cor como caractere de ponto
    de codigo baixo (\\x13, \\x80, \\xff). Codificar em EUC-JP os destruiria.
    """
    out = bytearray()
    for c in t:
        o = ord(c)
        if o < 0x100:
            out.append(o)
        else:
            out += c.encode(ENC, 'replace')
    return bytes(out)


def round_trip_ok(refeito, raw):
    """Round-trip tolerando o padding de zeros do fim do arquivo.

    O `v2069` ocupa 44.997 B uteis num span de 45.056: o `parse` nao guarda
    esse rabo de zeros e o `build` nao o reproduz. Exigir igualdade exata
    reprovaria um banco intacto — o que conta e' o conteudo util bater e o que
    sobra ser so' zero.
    """
    if refeito == raw:
        return True
    return (len(refeito) <= len(raw)
            and raw[:len(refeito)] == refeito
            and raw[len(refeito):].strip(NUL) == b'')


def faz_campofixo(raw, trad):
    p = campofixo.parse(raw)
    if not round_trip_ok(campofixo.build(p), raw):
        raise ValueError('round-trip do original falhou')
    n = 0
    for r in p['regs']:
        k = chave(r['raw'])
        if k in trad:
            novo = _enc(trad[k])
            if len(novo) >= campofixo.CAMPO:
                raise ValueError('registro %d: %d B nao cabe em %d B'
                                 % (r['i'], len(novo), campofixo.CAMPO - 1))
            r['raw'] = novo
            n += 1
    return campofixo.build(p), n, len(p['regs'])


def faz_oldata(raw, trad):
    p = oldata.parse(raw)
    if not round_trip_ok(oldata.build(p), raw):
        raise ValueError('round-trip do original falhou')
    # guarda em que LINHA da narracao cada episodio comeca, para reconstituir o
    # campo C depois que o texto mudar de tamanho
    starts, pos = [0], 0
    for l in p['narracao']:
        pos += len(l) + 1
        starts.append(pos)
    onde = {v: i for i, v in enumerate(starts)}
    idx = [onde.get(r[2], 0) for r in p['recs']]

    n = 0
    for campo in ('titulos', 'narracao'):
        novas = []
        for l in p[campo]:
            k = chave(l)
            if k in trad:
                novas.append(_enc(trad[k]))
                n += 1
            else:
                novas.append(l)
        p[campo] = novas
    oldata.recalcular_C(p, idx)
    return oldata.build(p), n, len(p['titulos']) + len(p['narracao'])


def faz_ptrtab(raw, trad):
    p = ptrtab.parse(raw)
    if not round_trip_ok(ptrtab.build(p), raw):
        raise ValueError('round-trip do original falhou')
    novas, n = [], 0
    for s in p['strings']:
        k = chave(s)
        if k in trad:
            novas.append(_enc(trad[k]))
            n += 1
        else:
            novas.append(s)
    p['strings'] = novas
    return ptrtab.build(p), n, len(novas)


FORMATOS = {'campofixo': faz_campofixo, 'oldata': faz_oldata, 'ptrtab': faz_ptrtab}
MODULO = {'campofixo': campofixo, 'oldata': oldata, 'ptrtab': ptrtab}


def textos_de(formato, parsed):
    if formato == 'campofixo':
        return [chave(r['raw']) for r in parsed['regs']]
    if formato == 'oldata':
        return ([chave(l) for l in parsed['titulos']]
                + [chave(l) for l in parsed['narracao']])
    return [chave(s) for s in parsed['strings']]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('formato', choices=sorted(FORMATOS))
    ap.add_argument('entrada_v', type=int)
    ap.add_argument('lotes', nargs='+')
    ap.add_argument('--arquivo', default=None,
                    help='nome do arquivo dentro do EZBIND (usado por ptrtab)')
    ap.add_argument('--aplicar', action='store_true')
    args = ap.parse_args()

    if os.path.abspath(args.iso_in) == os.path.abspath(args.iso_out):
        print('RECUSADO: entrada e saida sao a mesma ISO')
        return 1
    if 'Caravan.iso' in os.path.basename(args.iso_out):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1

    trad = carrega_lote(args.lotes)
    print('%d traducoes carregadas' % len(trad))

    base = LBA * SEC
    with open(args.iso_in, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        e = {x['v']: x for x in entries}.get(args.entrada_v)
        if not e:
            print('RECUSADO: entrada %d nao existe no bdi' % args.entrada_v)
            return 1
        f.seek(base + e['off'])
        blob = f.read(e['span'])

    pe = ezbind_parse(blob)
    dentro_ezbind = args.arquivo is not None and pe
    if dentro_ezbind:
        count, cab_do, regs = pe
        alvo = None
        for i, r in enumerate(regs):
            if r[0] == args.arquivo:
                alvo = (i, r)
                break
        if not alvo:
            print('RECUSADO: %s nao esta na entrada %d' % (args.arquivo, args.entrada_v))
            return 1
        i, (nome, no, sz, do, key) = alvo
        raw = blob[do:do + sz]
        gz = False
    else:
        gz = blob[:3] == GZ_MAGIC
        raw = gzip.decompress(blob) if gz else blob

    novo_raw, n, tot = FORMATOS[args.formato](raw, trad)
    print('%d de %d registros traduzidos' % (n, tot))
    print('banco: %d B -> %d B (%+d)' % (len(raw), len(novo_raw), len(novo_raw) - len(raw)))

    if dentro_ezbind:
        buraco = buraco_de(regs, i, len(blob))
        print('buraco disponivel: %d B' % buraco)
        if len(novo_raw) <= buraco:
            nb = bytearray(blob)
            nb[do:do + len(novo_raw)] = novo_raw
            for q in range(do + len(novo_raw), do + buraco):
                nb[q] = 0
            struct.pack_into('<I', nb, 0x10 + i * 16 + 4, len(novo_raw))
            novo_blob = bytes(nb)
            modo = 'in-place (buraco)'
        else:
            cand = ezbind_remonta(blob, regs, i, novo_raw, alinhamento(regs))
            if len(cand) > e['span']:
                print('RECUSADO: remontagem estoura o span em %d B'
                      % (len(cand) - e['span']))
                return 1
            novo_blob = cand + NUL * (e['span'] - len(cand))
            modo = 'remontagem do EZBIND'
    else:
        # `gzip_como_original` em vez de `gzip.compress`: preserva o cabecalho do
        # jogo byte a byte (MTIME/XFL/OS/FNAME) em vez de inventar um com FLG=0
        # e MTIME de agora — e, o que importa, garante UM bloco deflate so'
        # (P-79). `gzip.compress` ja dava um bloco so', mas sem guarda nenhuma.
        saida = gzip_como_original(novo_raw, blob) if gz else novo_raw
        if len(saida) > e['span']:
            print('RECUSADO: %d B nao cabe no span de %d B (faltam %d)'
                  % (len(saida), e['span'], len(saida) - e['span']))
            return 1
        novo_blob = saida + NUL * (e['span'] - len(saida))
        modo = 'gzip recomprimido (%d B)' % len(saida) if gz else 'arquivo cru, in-place'
    print('modo: %s' % modo)

    if not args.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    if not os.path.exists(args.iso_out):
        t0 = time.time()
        print('\ncopiando a ISO (%.2f GB)...' % (os.path.getsize(args.iso_in) / 2 ** 30),
              flush=True)
        shutil.copyfile(args.iso_in, args.iso_out)
        print('  copiada em %.0fs' % (time.time() - t0))
    if os.path.getsize(args.iso_out) != os.path.getsize(args.iso_in):
        print('RECUSADO: a saida mudou de tamanho')
        return 1

    off = base + e['off']
    with open(args.iso_out, 'r+b') as g:
        g.seek(off)
        g.write(novo_blob)
        g.flush()
        os.fsync(g.fileno())

    print('\nconferindo, relendo a ISO gerada...')
    with open(args.iso_out, 'rb') as g:
        g.seek(off)
        lido = g.read(e['span'])
    if lido != novo_blob:
        print('RECUSADO: a releitura do blob nao bate com o que foi escrito')
        return 1

    if dentro_ezbind:
        _, _, regs2 = ezbind_parse(lido)
        conf = lido[regs2[i][3]:regs2[i][3] + regs2[i][2]]
    elif gz:
        # NAO usar rstrip(NUL): o stream gzip pode terminar em zeros que fazem
        # parte dele, e cortar produz EOFError. `decompressobj` para sozinho no
        # fim do stream e ignora o padding que vem depois.
        conf = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(lido)
    else:
        conf = lido
    p2 = MODULO[args.formato].parse(conf)
    textos = set(textos_de(args.formato, p2))
    achou = sum(1 for t in trad.values() if t in textos)
    print('releitura: %d registros, %d das %d traducoes presentes'
          % (len(textos), achou, len(trad)))
    if achou < n:
        print('AVISO: %d traducoes aplicadas mas so %d conferidas na releitura'
              % (n, achou))
    print('-> %s' % args.iso_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

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
import sys, os, csv, gzip, zlib, struct, shutil, time, glob, argparse, bisect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import (ezbind_parse, buraco_de, alinhamento, ezbind_remonta,
                           gzip_como_original)
import campofixo, oldata, ptrtab, guia2
import textwrap, re
from largura_dupla import para_largura_dupla, tem_ascii

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


def faz_oldata(raw, trad, largura=None):
    p = oldata.parse(raw)
    if not round_trip_ok(oldata.build(p), raw):
        raise ValueError('round-trip do original falhou')
    # guarda em que LINHA da narracao cada episodio comeca, para reconstituir o
    # campo C depois que o texto mudar de tamanho
    starts, pos = [0], 0
    for l in p['narracao']:
        pos += len(l) + 1
        starts.append(pos)
    # C que cai no MEIO de uma linha (o episodio 15 do v2069, P-26) vai para o
    # inicio da linha que o contem. Antes era `onde.get(C, 0)`: o fallback
    # silencioso mandava o episodio para a linha 0, o episodio 14 ficava com
    # tamanho negativo e abrir a sinopse travava o jogo (P-83).
    idx = []
    for i, r in enumerate(p['recs']):
        j = bisect.bisect_right(starts, r[2]) - 1
        if starts[j] != r[2]:
            print('aviso: episodio %d comeca no byte %d da linha %d; vai para o '
                  'inicio dela' % (i, r[2] - starts[j], j))
        idx.append(j)

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
    if largura:
        idx = largura_dupla_oldata(p, idx, largura)
    oldata.recalcular_C(p, idx)
    oldata.recalcular_B(p)      # P-86: B e' o offset do titulo, nao dado opaco
    confere_episodios(oldata.parse(raw), p, linha_a_linha=not largura)
    return oldata.build(p), n, len(p['titulos']) + len(p['narracao'])


MARCA = '○○'.encode('euc_jp')
TROCA_MARCA = bytes([1, 2, 3, 4])   # o nome do jogador conta 4 colunas na quebra ("Player" = 3)
OO_ISOLADO = re.compile(rb'\bOO\b')


def quebra(linha, colunas):
    """Quebra uma linha em ingles em pedacos de ate' `colunas` caracteres, por
    palavra. O marcador do nome do jogador conta 4 colunas: o nome entra no lugar."""
    t = linha.replace(MARCA, TROCA_MARCA).decode('latin1')
    partes = textwrap.wrap(t, width=colunas, break_long_words=True,
                           break_on_hyphens=False) or ['']
    return [x.encode('latin1').replace(TROCA_MARCA, MARCA) for x in partes]


def largura_dupla_oldata(p, idx, colunas):
    """P-86: a tela de Sinopse desenha o `v2070` com caractere de 2 bytes. Converte
    titulos e narracao para largura dupla e quebra a narracao em linhas de ate'
    `colunas` caracteres (26 = a maior linha do original, a largura da caixa).
    Devolve os novos indices de linha de cada episodio.

    `OO` isolado no ingles e' sempre o nome do jogador (P-83): o tradutor o usou
    tambem onde o japones dizia so' "ele"/"ela". Vira marcador."""
    p['titulos'] = [para_largura_dupla(OO_ISOLADO.sub(MARCA, t)) for t in p['titulos']]
    fim = idx[1:] + [len(p['narracao'])]
    novas, novo_idx = [], []
    for a, b in zip(idx, fim):
        novo_idx.append(len(novas))
        bloco = [OO_ISOLADO.sub(MARCA, l) for l in p['narracao'][a:b]]
        if all(tem_ascii(l) for l in bloco):
            # episodio todo traduzido: junta e requebra corrido, para nao sobrar
            # linha de uma palavra so' onde a linha do tradutor terminava
            texto = b' '.join(l.strip() for l in bloco)
            novas.extend(para_largura_dupla(x) for x in quebra(texto, colunas))
        else:
            for l in bloco:
                if tem_ascii(l):
                    novas.extend(para_largura_dupla(x) for x in quebra(l, colunas))
                else:                              # japones que ficou sem traducao
                    novas.append(l)
    p['narracao'] = novas
    return novo_idx


def confere_episodios(orig, novo, linha_a_linha=True):
    """Guarda do P-83: todo episodio tem de comecar depois do anterior e ter o
    mesmo numero de linhas do original (a traducao e' linha a linha). A unica
    diferenca tolerada e' 1 linha, nos dois lados de um C que caia no meio."""
    def linhas(p):
        s, pos = [], 0
        for l in p['narracao']:
            s.append(pos)
            pos += len(l) + 1
        cs = [r[2] for r in p['recs']] + [pos]
        if any(b <= a for a, b in zip(cs, cs[1:])):
            raise ValueError('campo C fora de ordem: algum episodio ficaria com '
                             'tamanho zero ou negativo')
        ini = [bisect.bisect_right(s, c - 1) if c else 0 for c in cs]
        return [b - a for a, b in zip(ini, ini[1:])]
    pos = 0
    for i, t in enumerate(novo['titulos']):
        if novo['recs'][i][1] != pos:
            raise ValueError('campo B do episodio %d nao aponta para o titulo dele (P-86)' % i)
        pos += len(t) + 1
    lo, ln = linhas(orig), linhas(novo)
    if not linha_a_linha:           # a quebra muda o numero de linhas; a ordem basta
        return
    ruins = [(i, a, b) for i, (a, b) in enumerate(zip(lo, ln)) if abs(a - b) > 1]
    if ruins:
        raise ValueError('episodio(s) com numero de linhas diferente do original '
                         '(ep, orig, novo): %s' % ruins)


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


LF = chr(10)
TOKEN_LF = chr(92) + 'n'      # a quebra de linha como aparece no TSV (barra + n)


def faz_guia(raw, trad):
    """Guia/tutorial `v2065` (P-28, P-89), com o formato completo do `guia2.py`.

    O lote casa por TEXTO, como os outros bancos, com a quebra de linha do corpo
    escrita como o token barra+n no TSV. `guia2.build` recalcula os 2*count
    offsets de string; `recalcular_B` refaz o numero de linhas de cada corpo. O
    EBOOT nao guarda copia desses offsets (conferido, ao contrario do `v2070`)."""
    p = guia2.parse(raw)
    if guia2.build(p) != raw:
        raise ValueError('round-trip do original falhou')
    n = 0
    for r in p['regs']:
        for campo in ('titulo', 'corpo'):
            if not r[campo]:
                continue
            k = chave(r[campo]).replace(LF, TOKEN_LF)
            if k in trad:
                r[campo] = trad[k].replace(TOKEN_LF, LF).encode(ENC)
                n += 1
    guia2.recalcular_B(p)
    p['cauda'] = b''               # o span e o campo A se ajustam depois (P-87)
    return guia2.build(p), n, sum(1 for r in p['regs'] for c in ('titulo', 'corpo') if r[c])


FORMATOS = {'campofixo': faz_campofixo, 'oldata': faz_oldata, 'ptrtab': faz_ptrtab,
            'guia': faz_guia}
MODULO = {'campofixo': campofixo, 'oldata': oldata, 'ptrtab': ptrtab, 'guia': guia2}


def textos_de(formato, parsed):
    if formato == 'campofixo':
        return [chave(r['raw']) for r in parsed['regs']]
    if formato == 'oldata':
        return ([chave(l) for l in parsed['titulos']]
                + [chave(l) for l in parsed['narracao']])
    if formato == 'guia':
        return [chave(r[c]) for r in parsed['regs'] for c in ('titulo', 'corpo')]
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
    ap.add_argument('--largura-dupla', type=int, default=0, metavar='COLUNAS',
                    help='oldata: largura dupla + quebra da narracao em COLUNAS (P-86)')
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

    if args.largura_dupla and args.formato != 'oldata':
        print('RECUSADO: --largura-dupla so vale para oldata')
        return 1
    if args.formato == 'oldata':
        novo_raw, n, tot = faz_oldata(raw, trad, args.largura_dupla or None)
    else:
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
    if conf[:len(novo_raw)] != novo_raw or conf[len(novo_raw):].strip(NUL):
        print('RECUSADO: o banco relido nao e byte a byte o banco gerado')
        return 1
    print('releitura: banco identico ao gerado, byte a byte (%d B)' % len(novo_raw))
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

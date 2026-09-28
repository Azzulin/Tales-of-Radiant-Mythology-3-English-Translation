#!/usr/bin/env python3
"""Gera a ISO com o banco de texto .txz traduzido (TXZ-XX, P-60).

Uso:
  py txz_build_iso.py <iso_in> <lba> <catalogo.csv> <dir_lotes> <iso_out> [--aplicar] [--forcar]

DRY-RUN por padrao. Mesma politica de seguranca de `bdi_build_iso.py`: nunca
escreve na ISO original, so' escreve dentro do espaco que a entrada do bdi ja
ocupa, cena/arquivo que nao coube fica pulado com o japones intacto, e depois
de escrever RELE a ISO gerada e confere string por string.

## Por que isto e' uma ferramenta separada de `bdi_build_iso.py`

`.txz` nao e' FaceChat: sem gzip por cena (o gzip e' do CONTAINER EZBIND
inteiro, igual ao `.scr`, mas o CONTEUDO interno e' o formato `txz.py` —
tabela de offsets crescentes, sem terminador, **sem folga**, ver P-60). Uma
string mais curta que o orcamento tem os bytes que sobram preenchidos com
`\\x00` ate' o tamanho ORIGINAL exato — isso mantem TODOS os offsets da
tabela inalterados, entao nunca precisa recalcular nada dentro do `.txz`.
Reaproveita as funcoes de EZBIND/gzip de `bdi_build_iso.py` (mesmo container).
"""
import sys, os, re, csv, gzip, glob, collections
import txz
from bdi_build_iso import (
    ezbind_parse, buraco_de, alinhamento, ezbind_remonta,
    gzip_como_original, SEC,
)

NUL = b'\x00'
BARRA_N = chr(0x5C) + 'n'      # o token de quebra de linha do .txz — 0x5C 0x6E


def codifica(t):
    """Shift-JIS, SEM transformar a barra+n em 0x0A (P-82).

    `.txz` e `.scr` usam convencoes DIFERENTES de quebra de linha, e aplicar a
    de um no outro foi o que travou o jogo ao aceitar quest:

        `.scr` (dialogo)   CR+LF de verdade          0x0D 0x0A
        `.txz` (quadro)    o TOKEN de dois bytes     0x5C 0x6E

    Nos 767 `.txz` ORIGINAIS ha 3.190 tokens `barra+n` e **zero** bytes de
    controle — o renderizador do quadro de quest nunca viu um 0x0A na vida.
    Aqui a barra+n ja' e' o texto final: e' so' codificar.

    A guarda e' o que importa: qualquer byte < 0x20 na saida e' recusado,
    porque o original nao tem nenhum. Medido, nao suposto.
    """
    b = t.encode('shift_jis')
    ruins = sorted({x for x in b if x < 0x20})
    if ruins:
        raise ValueError(
            'byte de controle %s na traducao: o .txz original nao tem nenhum, '
            'a quebra de linha dele e o token %r (P-82) — %r'
            % ([hex(x) for x in ruins], BARRA_N, t[:60]))
    return b


def carrega_traducoes(dlotes):
    """{arquivo.txz: {indice: bytes_novos}} a partir de TXZ-XX_retorno.tsv.

    O `id` do lote ja' e' "<arquivo>:<indice>" — nao precisa de mapa externo
    (diferenca do FaceChat, onde o id e' cena:ordem e o indice vem de outro
    CSV). `arquivo` no TSV vem com o prefixo `v<entrada_v>_` (nome do
    ponteiro de extracao, ver `dados/strings_txz.csv`) — o catalogo do bdi
    guarda so' o nome do arquivo dentro do EZBIND, sem esse prefixo.
    """
    out = collections.defaultdict(dict)
    n = 0
    for nome in sorted(glob.glob(os.path.join(dlotes, 'TXZ-*_retorno.tsv'))):
        rows = list(csv.DictReader(open(nome, encoding='utf-8-sig'), delimiter='\t'))
        for r in rows:
            t = r.get('traducao', '')
            if not t.strip():
                continue
            arq = re.sub(r'^v\d+_', '', r['arquivo'])
            idx = int(r['id'].split(':')[1])
            out[arq][idx] = codifica(t)
            n += 1
    print(f'  {n} strings .txz traduzidas em {len(out)} arquivo(s)')
    return out


def monta_txz(raw, trad_arquivo):
    """Aplica as traducoes de um arquivo .txz, preenchendo ate o tamanho
    ORIGINAL de cada string com \\x00 (nunca estoura — EB ja garante isso)."""
    p = txz.parse(raw)
    mudou = False
    for s in p['strings']:
        novo = trad_arquivo.get(s['i'])
        if novo is None:
            continue
        if len(novo) > s['bytes']:
            raise ValueError(f"string {s['i']}: {len(novo)} B nao cabe no "
                              f"slot original de {s['bytes']} B")
        s['raw'] = novo + NUL * (s['bytes'] - len(novo))
        mudou = True
    return txz.build(p), mudou


def main():
    import shutil, time
    if len(sys.argv) < 6:
        print(__doc__)
        return 2
    iso_in, lba, cat, dlotes, iso_out = (sys.argv[1], int(sys.argv[2]), sys.argv[3],
                                         sys.argv[4], sys.argv[5])
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

    trad = carrega_traducoes(dlotes)
    if not trad:
        print('nenhuma traducao .txz encontrada — nada a fazer')
        return 1

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.endswith('.txz') and n in {k.lower() for k in trad}:
            porv[int(r['entrada_v'])].add(n)
    alvos = sum(len(v) for v in porv.values())
    print(f'arquivos .txz a reinserir: {alvos} em {len(porv)} entradas do bdi\n')
    if not alvos:
        print('nenhum .txz traduzido casou com o catalogo — nada a fazer')
        return 1

    trad_ci = {k.lower(): v for k, v in trad.items()}
    base = lba * SEC
    plano = []
    pulados = []
    with open(iso_in, 'rb') as f:
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
            confs = []
            for i, (nome, no, sz, do, key) in enumerate(regs):
                if nome.lower() not in porv[v]:
                    continue
                raw = novo_blob[do:do + sz]
                try:
                    dado = gzip.decompress(raw)
                except Exception as ex:
                    pulados.append((nome, f'{type(ex).__name__}: {ex}')); continue
                if not txz.round_trip_ok(dado):
                    pulados.append((nome, 'round-trip do txz falhou')); continue

                try:
                    novo_dado, mudou = monta_txz(dado, trad_ci[nome.lower()])
                except ValueError as ex:
                    pulados.append((nome, str(ex))); continue
                if not mudou:
                    continue
                if len(novo_dado) != len(dado):
                    pulados.append((nome, 'tamanho do .txz mudou — nao deveria')); continue

                novo_gz = gzip_como_original(novo_dado, raw)
                if gzip.decompress(novo_gz) != novo_dado:
                    pulados.append((nome, 'gzip novo nao descomprime igual')); continue

                buraco = buraco_de(regs, i, len(novo_blob))
                if len(novo_gz) <= buraco:
                    b = bytearray(novo_blob)
                    b[do:do + len(novo_gz)] = novo_gz
                    for q in range(do + len(novo_gz), do + buraco):
                        b[q] = 0
                    import struct
                    struct.pack_into('<I', b, 0x10 + i * 16 + 4, len(novo_gz))
                    novo_blob = bytes(b)
                    confs.append((nome, do, len(novo_gz), novo_dado))
                else:
                    cand = ezbind_remonta(novo_blob, regs, i, novo_gz, alin)
                    if len(cand) > e['span']:
                        pulados.append((nome, f'estoura o span em '
                                              f'{len(cand)-e["span"]} B')); continue
                    novo_blob = cand + b'\x00' * (e['span'] - len(cand))
                    regs = ezbind_parse(novo_blob)[2]
                    d2 = [r2 for r2 in regs if r2[0].lower() == nome.lower()][0]
                    confs.append((nome, d2[3], d2[2], novo_dado))
            if confs:
                assert len(novo_blob) == e['span'], 'span mudou de tamanho'
                plano.append((base + e['off'], novo_blob, e['span'], confs))

    n_arqs = sum(len(c[3]) for c in plano)
    print(f'PLANO: {len(plano)} entradas do bdi, {n_arqs} arquivo(s) .txz reinseridos, '
          f'{sum(c[2] for c in plano):,} bytes reescritos')
    print(f'       {len(pulados)} pulados (japones fica intacto)')
    for nm, m in pulados[:12]:
        print(f'         - {nm}: {m}')
    if not plano:
        print('\nNada coube. Nenhuma ISO seria gerada — o japones fica como esta.')
        return 1
    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    t0 = time.time()
    print(f'\ncopiando a ISO ({os.path.getsize(iso_in)/2**30:.2f} GB)...', flush=True)
    shutil.copyfile(iso_in, iso_out)
    print(f'  copiada em {time.time()-t0:.0f}s')
    assert os.path.getsize(iso_out) == os.path.getsize(iso_in), 'tamanho mudou na copia'

    with open(iso_out, 'r+b') as g:
        for off, blob, span, _ in plano:
            g.seek(off); g.write(blob)
        g.flush(); os.fsync(g.fileno())
    print(f'escrito. tamanho final: {os.path.getsize(iso_out):,} B '
          f'(igual? {os.path.getsize(iso_out) == os.path.getsize(iso_in)})')

    print('\nconferindo, relendo a ISO gerada...')
    ok = ruim = 0
    with open(iso_out, 'rb') as g:
        for off, blob, span, confs in plano:
            g.seek(off)
            lido = g.read(span)
            if lido != blob:
                print(f'  ! entrada em 0x{off:X} nao bate com o planejado'); ruim += 1; continue
            for nome, do, tam, esperado in confs:
                try:
                    dado = gzip.decompress(lido[do:do + tam])
                except Exception as ex:
                    print(f'  ! {nome}: {type(ex).__name__}'); ruim += 1; continue
                if dado != esperado:
                    print(f'  ! {nome}: conteudo difere do planejado'); ruim += 1
                else:
                    ok += 1
    print(f'  arquivos conferidos da ISO: {ok} corretos, {ruim} com falha')

    print('\ndiff por setor contra a original...')
    setores = set()
    BL = 8 << 20
    with open(iso_in, 'rb') as a, open(iso_out, 'rb') as b:
        pos = 0
        while True:
            x = a.read(BL); y = b.read(BL)
            if not x: break
            if x != y:
                for i in range(0, len(x), SEC):
                    if x[i:i+SEC] != y[i:i+SEC]:
                        setores.add((pos + i) // SEC)
            pos += len(x)
    dentro = set()
    for off, blob, span, _ in plano:
        for s in range(off // SEC, (off + span) // SEC):
            dentro.add(s)
    fora = setores - dentro
    print(f'  setores diferentes: {len(setores)}  | fora das entradas planejadas: {len(fora)}')
    print(f'  {"OK — nenhuma escrita fora do alvo" if not fora else "PROBLEMA: escreveu fora do alvo"}')
    print(f'\n-> {iso_out}')
    return 0 if (not ruim and not fora) else 1


if __name__ == '__main__':
    sys.exit(main())

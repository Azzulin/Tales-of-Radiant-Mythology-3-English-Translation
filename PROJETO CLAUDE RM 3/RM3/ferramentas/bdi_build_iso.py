#!/usr/bin/env python3
"""Gera a ISO com o dialogo traduzido. Ver P-51.

Uso:
  py bdi_build_iso.py <iso_original> <lba> <catalogo.csv> <dir_lotes> <iso_saida> [--aplicar]

DRY-RUN por padrao: sem --aplicar nao escreve byte nenhum.

## Seguranca

  * A ISO ORIGINAL nunca e' aberta para escrita. O script RECUSA se o nome de
    saida for igual ao de entrada, e recusa se a saida ja existir sem --forcar.
  * So' escreve DENTRO da faixa de setores que a entrada do bdi ja ocupa. O
    indice do bdi nao e' tocado, entao o campo A (P-14) nao entra na conta.
  * Cena que nao couber e' PULADA e listada — o japones dela fica intacto.
    Meio build e' pior que nenhum se ninguem souber o que ficou de fora.
  * Depois de escrever, RELE a ISO gerada e confere cada cena: descomprime,
    parseia e compara string por string com o que era para estar la'.

## Como a cena e' montada

  strings traduzidas  -> a traducao
  strings traduziveis sem traducao -> o JAPONES original (nao inventa nada)
  strings orfas (nome de arquivo, nota de producao) -> verbatim, sempre

Recomprime com zlib-9 (UM bloco deflate, como o jogo faz), preservando o cabecalho
byte a byte (MTIME, XFL, OS, FNAME do jogo).
"""
import sys, os, io, csv, gzip, zlib, struct, collections

SEC = 2048
FATOR_BRUTO = 1.10          # EN/JP medido em 429 falas reais dos lotes MEV-00a/00b
NIVEL_GZIP = 9


# ---------- EZBIND ----------

def ezbind_parse(blob):
    """Devolve (count, data_off_cab, [ (nome, name_off, size, data_off, key) ])."""
    if blob[:6] != b'EZBIND':
        return None
    count, = struct.unpack_from('<I', blob, 8)
    cab_do, = struct.unpack_from('<I', blob, 12)
    if not (0 < count <= 4000) or 0x10 + count * 16 > len(blob):
        return None
    regs = []
    for i in range(count):
        no, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(b'\x00', no) if no < len(blob) else -1
        nome = blob[no:z].decode('latin1') if z > no else ''
        regs.append((nome, no, sz, do, key))
    return count, cab_do, regs


def buraco_de(regs, i, tam_total):
    """Espaco fisico disponivel para o arquivo i, ate o inicio do proximo dado."""
    _, _, sz, do, _ = regs[i]
    proximos = [r[3] for r in regs if r[3] > do]
    fim = min(proximos) if proximos else tam_total
    return fim - do


def alinhamento(regs):
    """MEDE o alinhamento dos dados no EZBIND — nao presume.

    E' a maior potencia de 2 que divide todos os `data_off`. Se der 1, os dados
    nao sao alinhados e o remontador nao insere padding nenhum.
    """
    from math import gcd
    g = 0
    for r in regs:
        g = gcd(g, r[3])
    a = 1
    while a * 2 <= max(1, g) and g % (a * 2) == 0:
        a *= 2
    return a


def ezbind_remonta(blob, regs, i, novo_dado, alin=None):
    """Remonta o EZBIND trocando o arquivo i. Devolve bytes.

    Preserva cabecalho, pool de nomes e a ORDEM fisica dos dados; so' recalcula
    `size` e `data_off`. Nao reordena nada. O alinhamento e' MEDIDO do original.
    """
    if alin is None:
        alin = alinhamento(regs)
    ordem = sorted(range(len(regs)), key=lambda k: regs[k][3])
    base = min(r[3] for r in regs)
    out = bytearray(blob[:base])
    novos = {}
    pos = base
    for k in ordem:
        nome, no, sz, do, key = regs[k]
        dado = novo_dado if k == i else blob[do:do + sz]
        novos[k] = (pos, len(dado))
        out += dado
        falta = (-len(out)) % alin
        out += b'\x00' * falta
        pos = len(out)
    for k, (do, sz) in novos.items():
        nome, no, _, _, key = regs[k]
        struct.pack_into('<IIII', out, 0x10 + k * 16, no, sz, do, key)
    return bytes(out)


# ---------- FaceChat ----------

def fc_parse(d):
    if d[:8] != b'FaceChat':
        raise ValueError('sem magic FaceChat')
    a, n_str, n_tok, term = struct.unpack_from('<4H', d, 8)
    if term != 0xFFFF:
        raise ValueError('campo 0x0e != 0xffff')
    tok_end = 0x10 + n_tok * 2
    tbl_end = tok_end + n_str * 2
    offs = list(struct.unpack_from(f'<{n_str}H', d, tok_end)) if n_str else []
    ss = []
    for o in offs:
        p = tbl_end + o
        z = d.find(b'\x00', p)
        ss.append(d[p:z])
    return {'a': a, 'n_tok': n_tok, 'tokens': d[0x10:tok_end], 'strings': ss}


def fc_build(p, strings):
    body = bytearray()
    offs = []
    for s in strings:
        offs.append(len(body))
        body += s + b'\x00'
    if offs and offs[-1] > 0xFFFF:
        raise ValueError('bloco de strings passou de 65535 B — a tabela e u16')
    out = bytearray(b'FaceChat')
    out += struct.pack('<4H', p['a'], len(strings), p['n_tok'], 0xFFFF)
    out += p['tokens']
    for o in offs:
        out += struct.pack('<H', o)
    out += body
    return bytes(out)


# ---------- traducoes ----------

def carrega_mapas(dados_dir):
    """Junta o id->(cena,idx_string) de TODOS os *_falantes.csv em `dados/`.

    Cada frente FaceChat (mev/cev/qev/...) tem seu proprio `<prefixo>_falantes.csv`,
    gerado por `scr_falantes_dump.py --prefixo <X>` com o MESMO schema (P-56/P-58).
    Os `id` sao prefixados pelo nome da cena (`mev00_040:12`, `cev01_020:2`,
    `qev07_010:5`), entao nunca colidem entre frentes — juntar os mapas e' seguro.
    `elenco_falantes.csv` e outros CSVs sem as colunas certas sao ignorados.
    """
    import glob
    idx = {}
    achados = []
    for path in sorted(glob.glob(os.path.join(dados_dir, '*_falantes.csv'))):
        try:
            r0 = csv.DictReader(open(path, encoding='utf-8'))
            if not {'id', 'cena', 'idx_string'} <= set(r0.fieldnames or []):
                continue
            n = 0
            for r in r0:
                idx[r['id']] = (r['cena'], int(r['idx_string']))
                n += 1
            achados.append((os.path.basename(path), n))
        except (OSError, csv.Error):
            continue
    if not achados:
        print(f'ERRO: nenhum *_falantes.csv valido em {dados_dir} — e deles que vem o idx_string')
        sys.exit(2)
    for nome, n in achados:
        print(f'  mapa {nome}: {n} falas')
    return idx


def carrega_traducoes(d, idx):
    """{cena: {idx_string: bytes}} a partir dos *_retorno.tsv.

    O TSV do lote NAO traz `idx_string` — ele traz `id` (cena:ordem), que e' a
    ordem de EXIBICAO. O indice da string dentro do FaceChat vem do mapa
    combinado (`carrega_mapas`), e a juncao e' pelo `id`. Uma mesma string
    exibida duas vezes tem dois `id` e um `idx_string` so'.
    """
    out = collections.defaultdict(dict)
    traduziveis = collections.defaultdict(set)
    for cena, i in idx.values():
        traduziveis[cena].add(i)
    if not os.path.isdir(d):
        return out
    n = conflito = 0
    for nome in sorted(os.listdir(d)):
        if not nome.endswith('_retorno.tsv'):
            continue
        L = [l.split('\t') for l in open(os.path.join(d, nome), encoding='utf-8-sig')
             .read().split('\n') if l.strip()]
        cab = L[0]
        for linha in L[1:]:
            r = dict(zip(cab, linha))
            t = r.get('traducao', '')
            if not t.strip():
                continue
            alvo = idx.get(r.get('id', ''))
            if not alvo:
                continue
            cena, i = alvo
            b = t.replace('\\n', '\r\n').encode('euc_jp', 'replace')
            if i in out[cena] and out[cena][i] != b:
                conflito += 1
            out[cena][i] = b
            n += 1
    print(f'  {n} falas traduzidas mapeadas para indice de string'
          + (f'  ({conflito} conflitos — mesma string, traducao diferente!)' if conflito else ''))
    return out, traduziveis


try:
    import zopfli.gzip as _zop
except Exception:
    _zop = None


def cabecalho_gzip(gz):
    """Devolve o cabecalho do gzip ORIGINAL, byte a byte, e onde o deflate comeca.

    Nao inventa cabecalho: reusa o do jogo, com o MTIME, XFL, OS e FNAME que ele
    ja tem. So' o deflate e o rodape sao refeitos.
    """
    assert gz[:3] == b'\x1f\x8b\x08', 'nao e gzip deflate'
    flg = gz[3]
    i = 10
    if flg & 0x04:                       # FEXTRA
        xlen, = struct.unpack_from('<H', gz, i); i += 2 + xlen
    if flg & 0x08:                       # FNAME
        i = gz.index(b'\x00', i) + 1
    if flg & 0x10:                       # FCOMMENT
        i = gz.index(b'\x00', i) + 1
    if flg & 0x02:                       # FHCRC
        i += 2
    return gz[:i], i


def um_bloco_so(gz):
    """O deflate deste gzip tem UM bloco so'?

    BFINAL e' o bit 0 do primeiro byte do deflate (deflate le' bit a bit, do
    menos significativo para o mais). Se ele esta ligado no PRIMEIRO bloco,
    entao o primeiro bloco tambem e' o ultimo. Uma linha, e e' exatamente a
    pergunta que interessa (P-79).
    """
    _, i = cabecalho_gzip(gz)
    return bool(gz[i] & 1)


def gzip_como_original(dado, gz_original, usar_zopfli=False):
    """Recomprime `dado` mantendo o cabecalho do gzip original.

    **zlib nivel 9, NAO zopfli** — e a diferenca nao e' de tamanho, e' de
    formato. Decodificando bit a bit os `.scr` do jogo: TODO gzip original tem
    **um unico bloco deflate** (51 dinamicos, 8 fixos e 1 stored, numa amostra
    de 60). O zlib-9 reproduz essa distribuicao exatamente. O zopfli parte o
    fluxo em 2 a 5 blocos — legal pelo padrao, 6% menor, e **o descompressor do
    jogo le' so' o primeiro**: a cena chega truncada e o jogo trava ao carrega-la.

    Foi isso que travou toda ISO desde a `en09`, sempre na primeira cena
    traduzida que o jogador alcancava — por isso o ponto do travamento mudava
    de ISO para ISO (P-79). `usar_zopfli` fica so' para medicao comparativa;
    nenhum caminho de escrita deve liga-lo.
    """
    hdr, _ = cabecalho_gzip(gz_original)
    rodape = struct.pack('<II', zlib.crc32(dado) & 0xFFFFFFFF, len(dado) & 0xFFFFFFFF)
    if usar_zopfli and _zop is not None:
        z = _zop.compress(dado)          # gzip proprio, FLG=0, cabecalho de 10 B
        return hdr + z[10:-8] + rodape
    bio = io.BytesIO()
    g = gzip.GzipFile(mode='wb', compresslevel=NIVEL_GZIP, fileobj=bio, mtime=0)
    g.write(dado)
    g.close()
    novo = hdr + bio.getvalue()[10:-8] + rodape
    if not um_bloco_so(novo):
        raise ValueError('gzip novo tem mais de um bloco deflate — o jogo le '
                         'so o primeiro e trava (P-79)')
    return novo


def infla(s):
    """Simula o ingles para string sem traducao: mesmo conteudo, tamanho x FATOR."""
    alvo = max(1, int(len(s) * FATOR_BRUTO))
    base = b'The quick brown fox jumps over the lazy dog. '
    return (base * (alvo // len(base) + 1))[:alvo]



# ---------- principal ----------

def main():
    import shutil, hashlib, time
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

    dados_dir = os.path.join(os.path.dirname(os.path.abspath(dlotes)), 'dados')
    idx = carrega_mapas(dados_dir)
    trad, traduziveis = carrega_traducoes(dlotes, idx)
    print(f'traducoes carregadas: {len(trad)} cenas')
    print('compressor: zlib-9, um bloco deflate so (P-79 — zopfli parte o '
          'fluxo e o jogo le so o primeiro bloco)')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.endswith('.scr') and n in trad:
            porv[int(r['entrada_v'])].add(n)
    alvos = sum(len(v) for v in porv.values())
    print(f'cenas a reinserir: {alvos} em {len(porv)} entradas do bdi\n')
    if not alvos:
        print('nenhuma cena traduzida casou com o catalogo — nada a fazer')
        return 1

    base = lba * SEC
    plano = []      # (offset_absoluto_na_iso, bytes_novos, cena, conferencia)
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
            mudou = False
            confs = []
            for i, (nome, no, sz, do, key) in enumerate(regs):
                if nome.lower() not in porv[v]:
                    continue
                raw = novo_blob[do:do + sz]
                try:
                    scr = gzip.decompress(raw)
                    p = fc_parse(scr)
                except Exception as ex:
                    pulados.append((nome, f'{type(ex).__name__}: {ex}')); continue
                if fc_build(p, p['strings']) != scr:
                    pulados.append((nome, 'round-trip do FaceChat falhou')); continue

                tr = trad.get(nome.lower(), {})
                novas = []
                for k, orig in enumerate(p['strings']):
                    novas.append(tr[k] if k in tr else orig)
                try:
                    novo_scr = fc_build(p, novas)
                except ValueError as ex:
                    pulados.append((nome, str(ex))); continue
                novo_gz = gzip_como_original(novo_scr, raw)
                if gzip.decompress(novo_gz) != novo_scr:
                    pulados.append((nome, 'gzip novo nao descomprime igual')); continue

                buraco = buraco_de(regs, i, len(novo_blob))
                if len(novo_gz) <= buraco:
                    b = bytearray(novo_blob)
                    b[do:do + len(novo_gz)] = novo_gz
                    for q in range(do + len(novo_gz), do + buraco):
                        b[q] = 0
                    struct.pack_into('<I', b, 0x10 + i * 16 + 4, len(novo_gz))
                    novo_blob = bytes(b); mudou = True
                    confs.append((nome, do, len(novo_gz), novas))
                else:
                    cand = ezbind_remonta(novo_blob, regs, i, novo_gz, alin)
                    if len(cand) > e['span']:
                        pulados.append((nome, f'estoura o span em '
                                              f'{len(cand)-e["span"]} B')); continue
                    novo_blob = cand + b'\x00' * (e['span'] - len(cand))
                    regs = ezbind_parse(novo_blob)[2]
                    mudou = True
                    d2 = [r for r in regs if r[0].lower() == nome.lower()][0]
                    confs.append((nome, d2[3], d2[2], novas))
            if mudou:
                assert len(novo_blob) == e['span'], 'span mudou de tamanho'
                plano.append((base + e['off'], novo_blob, e['span'], confs))

    n_cenas = sum(len(c[3]) for c in plano)
    print(f'PLANO: {len(plano)} entradas do bdi, {n_cenas} cenas reinseridas, '
          f'{sum(c[2] for c in plano):,} bytes reescritos')
    print(f'       {len(pulados)} cenas puladas (japones fica intacto)')
    for nm, m in pulados[:12]:
        print(f'         - {nm}: {m}')
    if not plano:
        print('\nNada coube. Nenhuma ISO seria gerada — o japones fica como esta.')
        return 1
    if not aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    # --------- copia e escreve ---------
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

    # --------- confere relendo a ISO GERADA ---------
    print('\nconferindo, relendo a ISO gerada...')
    ok = ruim = 0
    with open(iso_out, 'rb') as g:
        for off, blob, span, confs in plano:
            g.seek(off)
            lido = g.read(span)
            if lido != blob:
                print(f'  ! entrada em 0x{off:X} nao bate com o planejado'); ruim += 1; continue
            for nome, do, tam, esperadas in confs:
                try:
                    scr = gzip.decompress(lido[do:do + tam])
                    p = fc_parse(scr)
                except Exception as ex:
                    print(f'  ! {nome}: {type(ex).__name__}'); ruim += 1; continue
                if p['strings'] != esperadas:
                    print(f'  ! {nome}: strings diferem do planejado'); ruim += 1
                else:
                    ok += 1
    print(f'  cenas conferidas da ISO: {ok} corretas, {ruim} com falha')

    # --------- diff por setor ---------
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

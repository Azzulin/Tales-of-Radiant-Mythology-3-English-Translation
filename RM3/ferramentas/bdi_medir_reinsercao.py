#!/usr/bin/env python3
"""Mede se a reinsercao de dialogo cabe SEM mexer no indice do bdi. Ver P-51.

Uso:
    python3 bdi_medir_reinsercao.py <iso> <lba> <catalogo.csv> <dir_lotes> [prefixo]

SOMENTE LEITURA. Nao escreve nada, em lugar nenhum. Abre a ISO em 'rb'.

## A pergunta

Trocar o japones por ingles muda o tamanho da cena. A cena mora assim:

    entrada do bdi  ->  EZBIND (cru)  ->  gzip  ->  FaceChat

Se o novo conteudo couber no mesmo numero de setores que a entrada ja ocupa, o
indice do bdi **nao muda** — e o campo A (P-14), que trava o projeto desde o
inicio, **nao entra na conta**. E o mesmo atalho que valeu para o EBOOT (P-44.5).

## Os dois niveis de folga, do mais seguro para o menos

  NIVEL 1 — in-place no EZBIND: o gzip novo cabe no buraco do gzip antigo
            (do `data_off` dele ate o `data_off` do proximo arquivo).
            Nada mais no EZBIND muda. E' o mais seguro que existe.

  NIVEL 2 — EZBIND reconstruido: o gzip novo e' maior que o buraco, mas o
            EZBIND inteiro, remontado, ainda cabe no span de setores da entrada.
            Muda `size` e `data_off` dos registros seguintes.

  ESTOURA — nem remontado cabe. So' ai' o indice do bdi teria de mudar.

## O que ele faz com cena sem traducao

Simula: infla cada string pelo fator medido nos lotes ja traduzidos (padrao 1.10
bruto). Cena simulada aparece marcada como `sim` na coluna `medido`, para que
ninguem confunda estimativa com medicao.
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

def carrega_traducoes(d, mapa_csv):
    """{cena: {idx_string: bytes}} a partir dos *_retorno.tsv.

    O TSV do lote NAO traz `idx_string` — ele traz `id` (cena:ordem), que e' a
    ordem de EXIBICAO. O indice da string dentro do FaceChat vem do
    `mev_falantes.csv`, e a juncao e' pelo `id`. Uma mesma string exibida duas
    vezes tem dois `id` e um `idx_string` so'.
    """
    out = collections.defaultdict(dict)
    if not os.path.isfile(mapa_csv):
        print(f'ERRO: nao achei {mapa_csv} — e dele que vem o idx_string')
        sys.exit(2)
    idx = {}
    traduziveis = collections.defaultdict(set)
    for r in csv.DictReader(open(mapa_csv, encoding='utf-8')):
        idx[r['id']] = (r['cena'], int(r['idx_string']))
        traduziveis[r['cena']].add(int(r['idx_string']))
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


def gzip_como_original(dado, gz_original, usar_zopfli=True):
    """Recomprime `dado` mantendo o cabecalho do gzip original.

    Com zopfli quando disponivel — mesmo formato, deflate melhor. Sem ele, cai
    para zlib nivel 9.
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
    return hdr + bio.getvalue()[10:-8] + rodape


def infla(s):
    """Simula o ingles para string sem traducao: mesmo conteudo, tamanho x FATOR."""
    alvo = max(1, int(len(s) * FATOR_BRUTO))
    base = b'The quick brown fox jumps over the lazy dog. '
    return (base * (alvo // len(base) + 1))[:alvo]


# ---------- principal ----------

def main():
    iso, lba, cat, dlotes = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    pref = sys.argv[5].lower() if len(sys.argv) > 5 else 'mev'
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bdi import load_index

    mapa = os.path.join(os.path.dirname(os.path.abspath(dlotes)), 'dados', 'mev_falantes.csv')
    trad, traduziveis = carrega_traducoes(dlotes, mapa)
    print(f'traducoes carregadas: {len(trad)} cenas')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.startswith(pref) and n.endswith('.scr'):
            porv[int(r['entrada_v'])].add(n)
    print(f'{sum(len(v) for v in porv.values())} cenas `{pref}` em {len(porv)} entradas\n')

    base = lba * SEC
    linhas = []
    falhas = []
    with open(iso, 'rb') as f:
        _, _, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        for v in sorted(porv):
            e = pore.get(v)
            if not e:
                falhas.append((v, 'entrada ausente')); continue
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            pe = ezbind_parse(blob)
            if not pe:
                falhas.append((v, 'nao e EZBIND')); continue
            count, cab_do, regs = pe
            for i, (nome, no, sz, do, key) in enumerate(regs):
                if nome.lower() not in porv[v]:
                    continue
                raw = blob[do:do + sz]
                try:
                    scr = gzip.decompress(raw)
                    p = fc_parse(scr)
                except Exception as ex:
                    falhas.append((nome, f'{type(ex).__name__}: {ex}')); continue
                if fc_build(p, p['strings']) != scr:
                    falhas.append((nome, 'round-trip do FaceChat falhou')); continue

                tr = trad.get(nome, {})
                tz = traduziveis.get(nome, set())
                medido = 'sim' if tr else ''
                # String ORFA (nome de arquivo, nota de producao, rotulo de efeito)
                # NUNCA e' tocada: o jogo a usa como dado, nao como texto. P-47.5.
                novas = []
                for k, orig in enumerate(p['strings']):
                    if k in tr:
                        novas.append(tr[k])          # traducao real
                    elif k in tz:
                        novas.append(infla(orig))    # traduzivel, ainda sem traducao
                    else:
                        novas.append(orig)           # orfa: verbatim
                try:
                    novo_scr = fc_build(p, novas)
                except ValueError as ex:
                    falhas.append((nome, str(ex))); continue
                # gzip com o mesmo nome interno do original (FNAME), como o jogo espera
                gz_zlib = gzip_como_original(novo_scr, raw, usar_zopfli=False)
                novo_gz = gzip_como_original(novo_scr, raw, usar_zopfli=True)
                # prova: o que o jogo vai descomprimir tem de ser identico
                if gzip.decompress(novo_gz) != novo_scr:
                    falhas.append((nome, 'gzip novo nao descomprime igual')); continue

                buraco = buraco_de(regs, i, len(blob))
                nivel1 = len(novo_gz) <= buraco
                alin = alinhamento(regs)
                novo_ez = ezbind_remonta(blob, regs, i, novo_gz, alin)
                nivel2 = len(novo_ez) <= e['span']
                nsect_novo = -(-len(novo_ez) // SEC)
                falta = max(0, len(novo_gz) - buraco) if not (nivel1 or nivel2) else 0

                linhas.append({
                    'cena': nome, 'entrada_v': v, 'medido': medido,
                    'strings_total': len(p['strings']),
                    'strings_traduziveis': len(tz), 'strings_com_traducao': len(tr),
                    'alinhamento_medido': alin,
                    'gz_original': sz, 'gz_novo': len(novo_gz),
                    'gz_novo_zlib9': len(gz_zlib),
                    'ganho_zopfli': len(gz_zlib) - len(novo_gz),
                    'delta_gz': len(novo_gz) - sz,
                    'bytes_a_economizar': falta,
                    'buraco_ezbind': buraco, 'cabe_inplace': 'sim' if nivel1 else '',
                    'ezbind_original': len(blob.rstrip(b'\x00')),
                    'ezbind_novo': len(novo_ez),
                    'span_setores': e['nsect'], 'setores_novo': nsect_novo,
                    'cabe_no_span': 'sim' if nivel2 else '',
                    'veredito': 'NIVEL 1 in-place' if nivel1 else
                                ('NIVEL 2 remontado' if nivel2 else 'ESTOURA'),
                })

    if not linhas:
        print('nenhuma cena medida — verifique os argumentos')
        return 1
    saida = os.path.join(dlotes, '..', 'dados', 'reinsercao_medida.csv')
    saida = os.path.normpath(saida)
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    c = collections.Counter(r['veredito'] for r in linhas)
    med = [r for r in linhas if r['medido']]
    print('=' * 64)
    print(f'{len(linhas)} cenas medidas  ({len(med)} com traducao real, '
          f'{len(linhas)-len(med)} simuladas a x{FATOR_BRUTO})')
    print('=' * 64)
    for k in ('NIVEL 1 in-place', 'NIVEL 2 remontado', 'ESTOURA'):
        n = c.get(k, 0)
        print(f'  {k:<20} {n:>4}  ({100*n//len(linhas)}%)')
    est = [r for r in linhas if r['veredito'] == 'ESTOURA']
    if est:
        print('\n  cenas que ESTOURAM o span:')
        for r in est[:12]:
            print(f"    {r['cena']:<18} gzip {r['gz_novo']:>5} B > buraco "
                  f"{r['buraco_ezbind']:>5} B  -> faltam "
                  f"{r['bytes_a_economizar']} B comprimidos")
    gz = sum(r['ganho_zopfli'] for r in linhas)
    print(f"\n  compressor: {'zopfli' if _zop else 'zlib-9 (zopfli AUSENTE — instale com: pip install zopfli)'}")
    if _zop:
        print(f'  ganho do zopfli sobre zlib-9: {gz:,} B no total, '
              f'{gz//max(1,len(linhas))} B por cena em media')
    d = [r['delta_gz'] for r in linhas]
    d.sort()
    print(f"\n  delta do gzip: mediana {d[len(d)//2]:+} B   "
          f"p90 {d[int(len(d)*.9)]:+} B   max {d[-1]:+} B")
    folga = [r['span_setores']*SEC - r['ezbind_novo'] for r in linhas]
    folga.sort()
    print(f"  folga no span depois de remontar: minima {folga[0]:+,} B   "
          f"mediana {folga[len(folga)//2]:+,} B")
    if falhas:
        print(f'\n  RECUSADAS ({len(falhas)}):')
        for n, m in falhas[:10]:
            print(f'    {n}: {m}')
    print(f'\n-> {saida}')
    print()
    if not est:
        print('VEREDITO: nenhuma cena estoura. O indice do bdi NAO precisa mudar,')
        print('e o campo A (P-14) nao entra na conta desta frente.')
    else:
        print(f'VEREDITO: {len(est)} cenas estouram. Essas precisam de tratamento —')
        print('encurtar o texto, ou responder o campo A do indice.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

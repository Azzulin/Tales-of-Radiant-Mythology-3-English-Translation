#!/usr/bin/env python3
"""Dumpa as frentes `mapD`/`mapShip` (texto de campo: placa, aviso, sinal) — P-65.

Uso: mapd_falas_extrai.py <iso> <lba> <catalogo.csv> <eboot> <saida.csv>

Cada cena `mapD<RR>A<NN>.scr` e `mapShip_<NN>.scr` fica presa a um objeto do
mapa de campo (placa de bifurcacao, alavanca, orbe misterioso, assento de
navio) — nao e' dialogo de personagem: quase toda linha e' `tipo=sistema`,
`escolha` ou `sem_caixa` (aviso, pergunta de confirmacao, texto ambiente).

Usa os DOIS mecanismos de exibicao ja conhecidos deste projeto — o `0x006B`/
extras de sempre (P-47, `facechat_falante.falas`) MAIS o `0x0276` novo (P-64,
achado em `nev`) — porque bateu de cara aqui tambem, em volume pequeno (2 de
815 strings brutas de `mapD`). O residuo depois dos dois (700 de 815 em
`mapD`) e' quase todo o MESMO punhado de ~9 verbos de interacao genericos
repetidos por sala (`調べる`/Examine, `セーブ`/Save, `押す`/Push, `引く`/Pull,
`倒す`/Defeat, `飛び降りる`/Jump down, `ワープ`/Warp, `移動`/Move, `開く`/Open,
`？？？`/???) mais identificador tecnico puro (`map_D03A22`, `point_32701`,
`start_N`) e letra solta em ASCII (ja "traduzida", nao e' japones) — excluido
por desenho, mesmo criterio de sempre (P-47.5): so entra quem um comando
comprovadamente exibe.

Somente leitura.
"""
import sys, csv, gzip, struct, collections
from bdi import load_index
import facechat, facechat_falante as FF

OP_LINHA_NEV = 0x0276  # ver nev_falas_extrai.py / P-64
SEC = 2048
ELENCO_VA = 0x08D66EB0
ELENCO_N = 114
PREFIXOS = ('mapd', 'mapship')


def ezbind(blob):
    if blob[:6] != b'EZBIND':
        return None
    count = struct.unpack_from('<I', blob, 8)[0]
    if not (0 < count <= 4000) or 0x10 + count * 16 > len(blob):
        return None
    out = []
    for i in range(count):
        no, sz, do, key = struct.unpack_from('<IIII', blob, 0x10 + i * 16)
        z = blob.find(b'\x00', no) if no < len(blob) else -1
        out.append((blob[no:z].decode('latin1') if z > no else '', sz, do))
    return out


def cenas_do_blob(blob, prof=0):
    if prof > 5:
        return {}
    if blob[:3] == b'\x1f\x8b\x08':
        try:
            return cenas_do_blob(gzip.decompress(blob), prof + 1)
        except Exception:
            return {}
    fs = ezbind(blob)
    if fs is None:
        return {}
    out = {}
    for nome, sz, do in fs:
        sub = blob[do:do + sz]
        if sub[:3] == b'\x1f\x8b\x08':
            try:
                sub = gzip.decompress(sub)
            except Exception:
                continue
        if sub[:8] == b'FaceChat':
            out[nome.lower()] = sub
        elif sub[:6] == b'EZBIND':
            out.update(cenas_do_blob(sub, prof + 1))
    return out


def falas_campo(p, elenco):
    """Uniao de facechat_falante.falas() (0x006B+extras) com o 0x0276 (P-64)."""
    base = FF.falas(p, elenco)
    vistos = {fa['idx'] for fa in base}
    out = list(base)
    ss = p['strings']
    for c in FF.comandos(p['tokens'], p['n_tok']):
        for i in range(len(c) - 2):
            if c[i] == OP_LINHA_NEV and 0 <= c[i + 2] < len(ss) and c[i + 2] not in vistos:
                idx = c[i + 2]
                try:
                    texto = ss[idx].decode('euc_jp')
                except UnicodeDecodeError:
                    continue
                out.append({'ordem': len(out), 'ator': None, 'falante': '(placa/sinal)',
                            'tipo': 'sem_caixa', 'idx': idx, 'bytes': len(ss[idx]),
                            'texto': texto, 'repetida': idx in vistos})
                vistos.add(idx)
    return out


def main():
    iso, lba, cat, eb, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
    import eboot_tabsis as T
    d = T.ler(eb)
    elenco = {}
    for e in T.entradas(d, ELENCO_VA, ELENCO_N):
        if e['off'] is not None:
            elenco[e['i']] = e['original'].decode('euc_jp')
    print(f'elenco: {len(elenco)} nomes')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.endswith('.scr') and any(n.startswith(p) for p in PREFIXOS):
            porv[int(r['entrada_v'])].add(n)
    total = sum(len(v) for v in porv.values())
    print(f'{total} cenas nos prefixos {PREFIXOS} em {len(porv)} entradas do bdi')

    base = lba * SEC
    stat = collections.Counter()
    ruins = []
    with open(iso, 'rb') as f, open(out, 'w', newline='', encoding='utf-8') as o:
        _, count, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        w = csv.writer(o)
        w.writerow(['id', 'cena', 'ordem', 'ator', 'falante', 'tipo', 'idx_string',
                    'bytes_jp', 'repetida', 'control_codes', 'original', 'traducao',
                    'status', 'nota'])
        for v in sorted(porv):
          e = pore.get(v)
          if not e:
              for nome in sorted(porv[v]):
                  ruins.append((nome, 'entrada v ausente'))
              continue
          f.seek(base + e['off'])
          achadas = cenas_do_blob(f.read(min(e['span'], 8 << 20)))
          for nome in sorted(porv[v]):
            blob = achadas.get(nome)
            try:
                if blob is None:
                    raise ValueError('cena nao achada dentro da entrada')
                if not facechat.round_trip_ok(blob):
                    raise ValueError('round-trip falhou')
                p = facechat.parse(blob)
            except Exception as ex:
                ruins.append((nome, f'{type(ex).__name__}: {ex}')); continue
            fs = falas_campo(p, elenco)
            stat['cenas'] += 1
            stat['falas'] += len(fs)
            for fa in fs:
                stat[fa['tipo']] += 1
                cc = []
                if '\r\n' in fa['texto']: cc.append(f"CRLF x{fa['texto'].count(chr(13)+chr(10))}")
                for tok in ('%s', '%d'):
                    if tok in fa['texto']: cc.append(f"{tok} x{fa['texto'].count(tok)}")
                w.writerow([f"{nome}:{fa['ordem']}", nome, fa['ordem'], fa['ator'] or '',
                            fa['falante'], fa['tipo'], fa['idx'], fa['bytes'],
                            'sim' if fa['repetida'] else '', ' '.join(cc),
                            fa['texto'].replace('\r\n', '\\n'), '', 'pendente', ''])
    print(f"\ncenas ok={stat['cenas']}  falas={stat['falas']}")
    print(f"  personagem={stat['personagem']}  narracao={stat['narracao']}  "
          f"escolha={stat['escolha']}  sistema={stat['sistema']}  sem_caixa={stat['sem_caixa']}")
    if ruins:
        print(f'RECUSADAS ({len(ruins)}):')
        for n, m in ruins[:10]:
            print(f'  {n}: {m}')
    print(f'-> {out}')


if __name__ == '__main__':
    main()

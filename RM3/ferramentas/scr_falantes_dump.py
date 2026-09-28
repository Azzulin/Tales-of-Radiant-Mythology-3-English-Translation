#!/usr/bin/env python3
"""Dumpa as cenas .scr COM falante para a tabela de strings. Ver P-47.

Uso: scr_falantes_dump.py <iso> <lba> <catalogo.csv> <eboot> <prefixo> <saida.csv>

Le direto da ISO (somente leitura) usando `entrada_v` do catalogo — uma entrada
gzip do bdi por cena. Valida round-trip de cada cena antes de emitir.
"""
import sys, csv, gzip, struct, collections
from bdi import load_index
import facechat, facechat_falante
import eboot_tabsis as T


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
    """Devolve {nome_minusculo: bytes do FaceChat} descendo gzip e EZBIND."""
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

SEC = 2048
ELENCO_VA = 0x08D66EB0
ELENCO_N = 114


def main():
    iso, lba, cat, eb, pref, out = (sys.argv[1], int(sys.argv[2]), sys.argv[3],
                                    sys.argv[4], sys.argv[5], sys.argv[6])
    d = T.ler(eb)
    elenco = {}
    for e in T.entradas(d, ELENCO_VA, ELENCO_N):
        if e['off'] is not None:
            elenco[e['i']] = e['original'].decode('euc_jp')
    print(f'elenco: {len(elenco)} nomes')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.startswith(pref) and n.endswith('.scr'):
            porv[int(r['entrada_v'])].add(n)
    total = sum(len(v) for v in porv.values())
    print(f'{total} cenas com prefixo {pref!r} em {len(porv)} entradas do bdi')

    base = lba * SEC
    stat = collections.Counter()
    atores = collections.Counter()
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
            fs = facechat_falante.falas(p, elenco)
            orf = facechat_falante.orfas(p, fs)
            stat['cenas'] += 1
            stat['falas'] += len(fs)
            stat['orfas'] += len(orf)
            for fa in fs:
                stat[fa['tipo']] += 1
                atores[(fa['ator'], fa['falante'])] += 1
                cc = []
                if '\r\n' in fa['texto']: cc.append(f"CRLF x{fa['texto'].count(chr(13)+chr(10))}")
                for tok in ('%s', '%d'):
                    if tok in fa['texto']: cc.append(f"{tok} x{fa['texto'].count(tok)}")
                w.writerow([f"{nome}:{fa['ordem']}", nome, fa['ordem'], fa['ator'],
                            fa['falante'], fa['tipo'], fa['idx'], fa['bytes'],
                            'sim' if fa['repetida'] else '', ' '.join(cc),
                            fa['texto'].replace('\r\n', '\\n'), '', 'pendente', ''])
    print(f"\ncenas ok={stat['cenas']}  falas={stat['falas']}  orfas={stat['orfas']}")
    print(f"  com personagem={stat['personagem']}  narracao={stat['narracao']}  "
          f"ator desconhecido={stat['desconhecido']}")
    if ruins:
        print(f'RECUSADAS ({len(ruins)}):')
        for n, m in ruins[:10]:
            print(f'  {n}: {m}')
    print(f'\natores distintos: {len(atores)}')
    for (a, nm), n in atores.most_common(20):
        print(f'  {a if a is not None else "-":>4} {nm:<20} {n:>5} falas')
    print(f'-> {out}')


if __name__ == '__main__':
    main()

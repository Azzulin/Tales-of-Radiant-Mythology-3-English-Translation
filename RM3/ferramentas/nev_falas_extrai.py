#!/usr/bin/env python3
"""Dumpa a frente `nev` (NPCs da guilda) para a tabela de strings. Ver P-64.

Uso: nev_falas_extrai.py <iso> <lba> <catalogo.csv> <saida.csv>

`nev` usa um comando de exibicao DIFERENTE de `mev`/`cev`/`qev`/`tev`: nao ha
opcode 0x006B (P-47) em nenhuma das 88 cenas. Em vez disso, o texto e' exibido
por um comando novo:

    0276  0001  <idx>  <n>   ...   0018

`idx` e' o indice da string (confirmado: cobre 0..n_strings-1 em 86 das 88
cenas). NAO ha campo de ator/elenco nesse comando — ao contrario de 0x006B,
que carrega <ator> explicito. Por isso `falante` sai como um rotulo generico
fixo ('(NPC da guilda)'), nao um nome — ver P-64 para o porque disso nao ser
um bug de extracao, e sim um limite real do formato ainda nao decifrado.

O residuo (string que nenhum 0276 exibe: 166 de 1933) e' menu de debug/dev
nunca visto no jogo publicado (unlock de mapa, remake de personagem, sound
test, dificuldade oculta...) — mesma categoria do residuo de producao achado
em P-47.4 para `mev`. Excluido por desenho, nao decidido aqui: uma string so'
entra na tabela se um comando a exibe (mesmo criterio de sempre).

Somente leitura.
"""
import sys, csv, gzip, struct, collections
from bdi import load_index
import facechat

OP_LINHA = 0x0276  # 0276 0001 <idx> <n> ... 0018 — exibe string[idx] (P-64)
SEC = 2048


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


def comandos(tokens, n_tok):
    tok = list(struct.unpack_from(f'<{n_tok}H', tokens, 0))
    cmds, cur = [], []
    for t in tok:
        if t == 0xFFFF:
            cmds.append(cur); cur = []
        else:
            cur.append(t)
    if cur:
        cmds.append(cur)
    return cmds


def falas_nev(p):
    """Indices de string exibidos por 0276, na ORDEM em que aparecem no stream."""
    ss = p['strings']
    out = []
    vistos = set()
    for c in comandos(p['tokens'], p['n_tok']):
        for i in range(len(c) - 2):
            if c[i] == OP_LINHA and 0 <= c[i + 2] < len(ss):
                idx = c[i + 2]
                try:
                    texto = ss[idx].decode('euc_jp')
                except UnicodeDecodeError:
                    continue
                out.append({'ordem': len(out), 'idx': idx, 'bytes': len(ss[idx]),
                            'texto': texto, 'repetida': idx in vistos})
                vistos.add(idx)
    return out


def main():
    iso, lba, cat, out = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(cat, encoding='utf-8')):
        n = r['nome'].lower()
        if n.startswith('nev') and n.endswith('.scr'):
            porv[int(r['entrada_v'])].add(n)
    total = sum(len(v) for v in porv.values())
    print(f'{total} cenas com prefixo \'nev\' em {len(porv)} entradas do bdi')

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
            fs = falas_nev(p)
            stat['cenas'] += 1
            stat['falas'] += len(fs)
            stat['residuo'] += len(p['strings']) - len({fa['idx'] for fa in fs})
            for fa in fs:
                cc = []
                if '\r\n' in fa['texto']: cc.append(f"CRLF x{fa['texto'].count(chr(13)+chr(10))}")
                for tok in ('%s', '%d'):
                    if tok in fa['texto']: cc.append(f"{tok} x{fa['texto'].count(tok)}")
                w.writerow([f"{nome}:{fa['ordem']}", nome, fa['ordem'], '',
                            '(NPC da guilda)', 'personagem', fa['idx'], fa['bytes'],
                            'sim' if fa['repetida'] else '', ' '.join(cc),
                            fa['texto'].replace('\r\n', '\\n'), '', 'pendente', ''])
    print(f"\ncenas ok={stat['cenas']}  falas={stat['falas']}  residuo (nao exibido)={stat['residuo']}")
    if ruins:
        print(f'RECUSADAS ({len(ruins)}):')
        for n, m in ruins[:10]:
            print(f'  {n}: {m}')
    print(f'-> {out}')


if __name__ == '__main__':
    main()

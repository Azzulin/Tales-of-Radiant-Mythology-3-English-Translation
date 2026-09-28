#!/usr/bin/env python3
"""Cobertura de traducao do `namco.bdi`: quanta fala de `.scr` ainda tem japones.

Contraparte da `eboot_cobertura.py` (P-68), para o outro lado do jogo. Mesma
pergunta, mesma motivacao: as frentes de dialogo foram achadas por prefixo de
nome (`mev`, `cev`, `qev`, ...) e nunca por varredura, entao "acabou" nunca foi
medido — so' suposto.

Abre CADA `.scr` do catalogo, faz o round-trip do FaceChat e conta as falas que
ainda tem caractere japones, separando:

  - cenas que o projeto ja extraiu (estao em algum `dados/*_falantes.csv`)
  - cenas que NUNCA foram extraidas

Somente leitura, e so' na ISO original — nunca escreve nada.

Uso:
  bdi_cobertura.py <iso> <lba> <catalogo.csv> [--prefixo P] [--saida CSV]
"""
import sys, csv, gzip, struct, collections, argparse, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
import facechat

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


# Faixas de escrita japonesa DE VERDADE. Contar "par EUC-JP valido" nao serve:
# `○○` (o marcador do nome do jogador) e `▲▲` sao pares validos e aparecem
# DENTRO da linha ja' traduzida. Medindo assim, 543 falas em ingles da `en18`
# eram contadas como japonesas — 38% do total acusado (P-80).
KANA_INI, KANA_FIM = 0x3040, 0x30FF      # hiragana + katakana
KANJI_INI, KANJI_FIM = 0x4E00, 0x9FFF    # ideogramas
LARG_INI, LARG_FIM = 0xFF66, 0xFF9D      # katakana de meia largura


def tem_jp(b):
    """Verdadeiro so' se houver kana ou kanji — nao mero par EUC-JP valido.

    Simbolo de largura dupla (○ ▲ ★ ～) decodifica como par valido e
    sobrevive de proposito na traducao: `○○` e' onde o jogo escreve o nome do
    jogador. Tratar isso como japones inflava a conta e fazia uma linha
    perfeitamente traduzida parecer pendente.
    """
    try:
        t = b.decode('euc_jp')
    except UnicodeDecodeError:
        t = b.decode('euc_jp', 'ignore')
    return any(KANA_INI <= ord(c) <= KANA_FIM
               or KANJI_INI <= ord(c) <= KANJI_FIM
               or LARG_INI <= ord(c) <= LARG_FIM for c in t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('lba', type=int)
    ap.add_argument('catalogo')
    ap.add_argument('--prefixo', default='')
    ap.add_argument('--saida', default='dados/bdi_cobertura.csv')
    ap.add_argument('--dados', default='dados')
    args = ap.parse_args()

    # cenas ja extraidas pelo projeto
    extraidas = set()
    import glob
    for p in glob.glob(os.path.join(args.dados, '*_falantes.csv')):
        try:
            rows = list(csv.DictReader(open(p, encoding='utf-8')))
        except Exception:
            continue
        if rows and 'cena' in rows[0]:
            extraidas |= {r['cena'].lower() for r in rows}
    print(f'{len(extraidas)} cenas ja extraidas pelo projeto')

    porv = collections.defaultdict(set)
    for r in csv.DictReader(open(args.catalogo, encoding='utf-8')):
        n = r['nome'].lower()
        if n.endswith('.scr') and n.startswith(args.prefixo):
            porv[int(r['entrada_v'])].add(n)
    total = sum(len(v) for v in porv.values())
    print(f'{total} cenas .scr no catalogo, em {len(porv)} entradas do bdi\n')

    base = args.lba * SEC
    st = collections.Counter()
    porfrente = collections.defaultdict(lambda: collections.Counter())
    linhas = []
    ruins = []
    with open(args.iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        feito = 0
        for v in sorted(porv):
            e = pore.get(v)
            if not e:
                for nome in porv[v]:
                    ruins.append((nome, 'entrada v ausente'))
                continue
            f.seek(base + e['off'])
            achadas = cenas_do_blob(f.read(min(e['span'], 8 << 20)))
            for nome in sorted(porv[v]):
                feito += 1
                if feito % 250 == 0:
                    print(f'  ... {feito}/{total}')
                blob = achadas.get(nome)
                if blob is None:
                    ruins.append((nome, 'nao achada na entrada'))
                    continue
                try:
                    p = facechat.parse(blob)
                except Exception as ex:
                    ruins.append((nome, f'{type(ex).__name__}'))
                    continue
                strs = p['strings']
                njp = sum(1 for s in strs if tem_jp(s))
                fr = ''.join(c for c in nome.split('.')[0] if not c.isdigit())[:8]
                ja = nome in extraidas
                st['cenas'] += 1
                st['cenas_extraidas' if ja else 'cenas_nunca_extraidas'] += 1
                st['falas_jp'] += njp
                porfrente[fr]['cenas'] += 1
                porfrente[fr]['jp'] += njp
                if not ja:
                    porfrente[fr]['jp_nao_extraido'] += njp
                    porfrente[fr]['cenas_nao_extraidas'] += 1
                linhas.append([nome, fr, 'sim' if ja else 'NAO', len(strs), njp])

    print(f'\ncenas lidas: {st["cenas"]}  (ja extraidas {st["cenas_extraidas"]}, '
          f'nunca extraidas {st["cenas_nunca_extraidas"]})')
    print(f'falas com japones no total: {st["falas_jp"]}')
    if ruins:
        print(f'{len(ruins)} cenas nao lidas (ex: {ruins[:3]})')

    print(f'\n{"frente":<12}{"cenas":>7}{"nao extr":>10}{"falas JP":>10}'
          f'{"JP nao extraido":>17}')
    print('-' * 58)
    for fr, c in sorted(porfrente.items(), key=lambda kv: -kv[1]['jp_nao_extraido']):
        print(f'{fr:<12}{c["cenas"]:>7}{c["cenas_nao_extraidas"]:>10}'
              f'{c["jp"]:>10}{c["jp_nao_extraido"]:>17}')

    with open(args.saida, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['cena', 'frente', 'ja_extraida', 'strings', 'falas_jp'])
        w.writerows(linhas)
    print(f'\n-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

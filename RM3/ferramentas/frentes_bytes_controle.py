#!/usr/bin/env python3
"""Compara o REPERTORIO DE BYTES DE CONTROLE de cada frente de texto, entre a
ISO original e uma ISO gerada (P-82).

Todas as verificacoes que o projeto tinha perguntavam "a estrutura esta
coerente?". Nenhuma perguntava **"o conteudo se parece com o que o jogo
escreve?"** — e foi por isso que 3.190 bytes 0x0A entraram no `.txz`, que no
original nao tem um unico byte < 0x20, e travaram o jogo ao aceitar quest.

O invariante e' barato e nunca tinha sido medido: *quais bytes de controle
existem no original desta frente?* Se o original nao tem um byte, o build nao
pode produzi-lo. E se tem, tem de produzir na mesma proporcao.

Cada frente tem sua propria convencao, e elas NAO se transferem:

    .scr  dialogo, EUC-JP      CR+LF de verdade (0x0D 0x0A)
    .txz  quadro, Shift-JIS    o token de dois bytes barra+n (0x5C 0x6E), zero controle
    EBOOT ASCII                0x0A de verdade

Somente leitura nas duas ISOs.

Uso:
  frentes_bytes_controle.py <iso_original> <iso_nova> [--lba 106896]
"""
import sys, os, gzip, zlib, csv, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse, fc_parse
import txz, campofixo, oldata, ptrtab

SEC = 2048
GZ = b'\x1f\x8b\x08'
MAGIC = b'FaceChat'
NUL = 0x00


def desgz(b):
    if b[:3] == GZ:
        return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(b)
    return b


def entrada(f, base, ents, v):
    e = {q['v']: q for q in ents}.get(v)
    if not e:
        return None
    f.seek(base + e['off'])
    return f.read(e['span'])


def conta(strings, ignora_nul=True):
    """{byte de controle: quantas vezes} sobre uma lista de bytes."""
    c = collections.Counter()
    for s in strings:
        for x in s:
            if x < 0x20 and not (ignora_nul and x == NUL):
                c[x] += 1
    return c


def cenas_do_blob(blob, prof=0):
    if prof > 5:
        return {}
    if blob[:3] == GZ:
        try:
            return cenas_do_blob(gzip.decompress(blob), prof + 1)
        except Exception:
            return {}
    pe = ezbind_parse(blob)
    if not pe:
        return {}
    out = {}
    for nome, no, sz, do, key in pe[2]:
        sub = blob[do:do + sz]
        if sub[:3] == GZ:
            try:
                sub = gzip.decompress(sub)
            except Exception:
                continue
        if sub[:8] == MAGIC:
            out[nome.lower()] = sub
        elif sub[:6] == b'EZBIND':
            out.update(cenas_do_blob(sub, prof + 1))
    return out


def frente_txz(f, base, ents):
    blob = entrada(f, base, ents, 1424)
    out = []
    if not blob:
        return out
    pe = ezbind_parse(blob)
    if not pe:
        return out
    for nome, no, sz, do, key in pe[2]:
        if nome.lower().endswith('.txz'):
            for s in txz.parse(desgz(blob[do:do + sz]))['strings']:
                out.append(s['raw'])
    return out


def frente_scr(f, base, ents, limite):
    out = []
    n = 0
    for e in ents:
        if limite and n >= limite:
            break
        f.seek(base + e['off'])
        for nome, b in cenas_do_blob(f.read(min(e['span'], 8 << 20))).items():
            try:
                p = fc_parse(b)
            except Exception:
                continue
            n += 1
            out.extend(p['strings'])
    return out


def frente_campofixo(f, base, ents):
    blob = entrada(f, base, ents, 2063)
    if not blob:
        return []
    # so' o conteudo util de cada registro, nao o padding do campo de 64 B
    return [r['raw'] for r in campofixo.parse(desgz(blob))['regs']]


def frente_oldata(f, base, ents, v):
    blob = entrada(f, base, ents, v)
    if not blob:
        return []
    p = oldata.parse(desgz(blob))
    return list(p['titulos']) + list(p['narracao'])


def frente_ptrtab(f, base, ents, arquivo):
    blob = entrada(f, base, ents, 3082)
    if not blob:
        return []
    pe = ezbind_parse(blob)
    if not pe:
        return []
    for nome, no, sz, do, key in pe[2]:
        if nome == arquivo:
            return list(ptrtab.parse(desgz(blob[do:do + sz]))['strings'])
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_orig')
    ap.add_argument('iso_nova')
    ap.add_argument('--lba', type=int, default=106896)
    ap.add_argument('--limite-scr', type=int, default=400,
                    help='quantas cenas .scr amostrar (0 = todas, e demora)')
    args = ap.parse_args()

    base = args.lba * SEC
    fa = open(args.iso_orig, 'rb')
    fb = open(args.iso_nova, 'rb')
    _, _, ents, _ = load_index(fa, base)

    FRENTES = [
        ('.txz  quadro de quest', lambda f: frente_txz(f, base, ents)),
        ('.scr  dialogo', lambda f: frente_scr(f, base, ents, args.limite_scr)),
        ('v2063 titulos de skit', lambda f: frente_campofixo(f, base, ents)),
        ('v2069 sinopse', lambda f: frente_oldata(f, base, ents, 2069)),
        ('v2070 titulos de capitulo', lambda f: frente_oldata(f, base, ents, 2070)),
        ('v3082 CName', lambda f: frente_ptrtab(f, base, ents, 'CharGuideTextCName.bin')),
        ('v3082 ORG', lambda f: frente_ptrtab(f, base, ents, 'CharGuideTextORG.bin')),
        ('v3082 TOW3', lambda f: frente_ptrtab(f, base, ents, 'CharGuideTextTOW3.bin')),
    ]

    print(f'{"frente":<28}{"controle no ORIGINAL":<34}{"controle na NOVA":<34}')
    print('-' * 96)
    alertas = []
    for rot, fn in FRENTES:
        try:
            a = conta(fn(fa))
            b = conta(fn(fb))
        except Exception as ex:
            print(f'{rot:<28}ERRO: {type(ex).__name__}: {ex}')
            continue
        fa_s = ' '.join(f'{hex(k)}x{v}' for k, v in sorted(a.items())) or '(nenhum)'
        fb_s = ' '.join(f'{hex(k)}x{v}' for k, v in sorted(b.items())) or '(nenhum)'
        marca = ''
        novos = sorted(set(b) - set(a))
        if novos:
            marca = '  <== INTRODUZIU ' + ','.join(hex(x) for x in novos)
            alertas.append((rot, novos, 'byte que o original nao tem'))
        sumiu = sorted(set(a) - set(b))
        if sumiu:
            marca += '  <== PERDEU ' + ','.join(hex(x) for x in sumiu)
            alertas.append((rot, sumiu, 'byte do original que sumiu'))
        # O tipo continuar existindo nao basta: a sinopse manteve 0x13 e 0x14 e
        # mesmo assim perdeu 147 dos 285 pares de codigo de cor (P-82.1). Um
        # codigo de controle costuma ser marcacao pareada — se a contagem cai,
        # texto que devia estar colorido/formatado deixou de estar.
        for k in sorted(set(a) & set(b)):
            if a[k] and abs(b[k] - a[k]) * 100 // a[k] >= 5:
                marca += f'  <== {hex(k)} {a[k]}->{b[k]}'
                alertas.append((rot, [k],
                                f'contagem de {hex(k)} mudou {a[k]} -> {b[k]}'))
        print(f'{rot:<28}{fa_s:<34}{fb_s:<34}{marca}')
    fa.close(); fb.close()

    print()
    if alertas:
        print(f'*** {len(alertas)} ALERTAS ***')
        for rot, bs, m in alertas:
            print(f'   {rot}: {m} — {[hex(x) for x in bs]}')
        return 1
    print('nenhuma frente introduziu ou perdeu byte de controle')
    return 0


if __name__ == '__main__':
    sys.exit(main())

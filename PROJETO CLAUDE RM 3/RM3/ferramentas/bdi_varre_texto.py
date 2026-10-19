#!/usr/bin/env python3
"""Varre TODO o `namco.bdi` atras de texto japones fora dos formatos ja
catalogados (P-68.3).

`bdi_cobertura.py` cobriu os `.scr`. Este cobre o resto: 83.809 entradas que nao
sao audio/modelo/textura — `.bin`, `.ppt`, `.ani`, NBI e afins — que nunca foram
varridas por texto. A pergunta e' a mesma das outras duas varreduras: alguem
supos que acabou, ninguem mediu.

Criterio: KANA OBRIGATORIO, em Shift-JIS e em EUC-JP. Kanji sozinho colide
demais com binario (tabela de ponteiro, float, indice), e foi o que gerou os 3
falsos positivos da varredura dos `battle_prx`. Exigir hiragana/katakana em
sequencia derruba isso quase a zero.

Somente leitura, e so' na ISO original.

Uso:
  bdi_varre_texto.py <iso> <lba> <catalogo.csv> [--saida CSV] [--min-kana 3]
"""
import sys, csv, gzip, struct, collections, argparse, os, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index

SEC = 2048
NUL = b'\x00'
# tipos sem texto por natureza
MUDO = {'RIFF', 'MDL', 'gzip>MDL', 'NOD', 'gzip>NOD', 'TXL', 'gzip>TXL',
        'PPHD', 'BMP', 'gzip>RIFF'}
# ja cobertos por outra frente/ferramenta
COBERTO = re.compile(r'\.scr$|\.txz$|CharGuideText|oldata', re.I)
# bancos que outra frente ja extraiu e que moram em entrada SEM nome de arquivo
# (por isso nao caem no COBERTO acima): v2063 titulos de skit, v2065 guia,
# v2069 sinopse, v2070 oldata, v3082 fichas de personagem
V_COBERTO = {2063, 2065, 2069, 2070, 3082}

# kana em Shift-JIS: hiragana 0x829F-0x82F1, katakana 0x8340-0x8396
SJIS_KANA = re.compile(rb'(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]){3,}')
# kana em EUC-JP: hiragana 0xA4A1-0xA4F3, katakana 0xA5A1-0xA5F6
EUC_KANA = re.compile(rb'(?:\xa4[\xa1-\xf3]|\xa5[\xa1-\xf6]){3,}')


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


def arquivos(blob, prof=0):
    """{nome: bytes} descendo gzip e EZBIND, como as outras ferramentas."""
    if prof > 5:
        return {}
    if blob[:3] == b'\x1f\x8b\x08':
        try:
            return arquivos(gzip.decompress(blob), prof + 1)
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
        if sub[:6] == b'EZBIND':
            out.update(arquivos(sub, prof + 1))
        else:
            out[nome] = sub
    return out


def plausivel(t):
    """Separa frase de lixo binario que caiu na faixa de kana.

    O lixo de `.ppt`/`.ani` (float, matriz) decodifica como repeticao pobre —
    'ャャモャ', 'いいいい'. Texto de verdade tem variedade e, quase sempre,
    kanji junto do kana.
    """
    if len(t) < 3:
        return False
    if len(set(t)) < 3:                       # 'ャャャ', 'いいいい'
        return False
    if len(set(t)) / len(t) < 0.4:            # repeticao demais
        return False
    kanji = sum(1 for c in t if '一' <= c <= '鿿')
    kana = sum(1 for c in t if '぀' <= c <= 'ヿ')
    outros = len(t) - kanji - kana
    if outros > len(t) * 0.5:                 # metade nao e japones: lixo
        return False
    return kanji > 0 or kana >= 4


def acha(blob, minkana):
    """Devolve [(codec, trecho_decodificado)] dos runs de kana."""
    out = []
    for rx, cod in ((SJIS_KANA, 'shift_jis'), (EUC_KANA, 'euc_jp')):
        for m in rx.finditer(blob):
            if (m.end() - m.start()) // 2 < minkana:
                continue
            # alarga ate o terminador, para pegar a frase inteira
            i = blob.rfind(b'\x00', max(0, m.start() - 120), m.start())
            i = i + 1 if i >= 0 else m.start()
            j = blob.find(b'\x00', m.end(), m.end() + 120)
            j = j if j >= 0 else m.end()
            try:
                t = blob[i:j].decode(cod)
            except Exception:
                try:
                    t = blob[m.start():m.end()].decode(cod)
                except Exception:
                    continue
            t = t.strip()
            # texto de verdade e delimitado por NUL dos dois lados
            bordado = (i == 0 or blob[i-1:i] == NUL) and                       (j >= len(blob) or blob[j:j+1] == NUL)
            if t and bordado and plausivel(t):
                out.append((cod, t))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('lba', type=int)
    ap.add_argument('catalogo')
    ap.add_argument('--saida', default='dados/bdi_varredura_texto.csv')
    ap.add_argument('--min-kana', type=int, default=3)
    args = ap.parse_args()

    porv = collections.defaultdict(list)
    for r in csv.DictReader(open(args.catalogo, encoding='utf-8')):
        if r['tipo'] in MUDO or COBERTO.search(r['nome']):
            continue
        if int(r['entrada_v']) in V_COBERTO:
            continue
        porv[int(r['entrada_v'])].append(r['nome'])
    print(f'{sum(len(v) for v in porv.values())} arquivos candidatos '
          f'em {len(porv)} entradas do bdi\n')

    base = args.lba * SEC
    achados = []
    porarq = collections.Counter()
    feito = 0
    with open(args.iso, 'rb') as f:
        _, count, entries, _ = load_index(f, base)
        pore = {e['v']: e for e in entries}
        for v in sorted(porv):
            feito += 1
            if feito % 500 == 0:
                print(f'  ... {feito}/{len(porv)} entradas, '
                      f'{len(achados)} trechos')
            e = pore.get(v)
            if not e:
                continue
            f.seek(base + e['off'])
            blob = f.read(min(e['span'], 16 << 20))
            fs = arquivos(blob)
            if not fs:
                fs = {f'(entrada_v {v})': blob}
            alvo = set(porv[v])
            for nome, sub in fs.items():
                if COBERTO.search(nome):
                    continue
                for cod, t in acha(sub, args.min_kana):
                    achados.append([v, nome, cod, len(t), t[:200]])
                    porarq[nome] += 1

    print(f'\n{len(achados)} trechos com kana achados, '
          f'em {len(porarq)} arquivos distintos\n')
    print(f'{"arquivo":<44}{"trechos":>8}')
    print('-' * 54)
    for k, n in porarq.most_common(25):
        print(f'{k:<44}{n:>8}')

    with open(args.saida, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['entrada_v', 'arquivo', 'codec', 'chars', 'texto'])
        w.writerows(achados)
    print(f'\n-> {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

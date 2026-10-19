#!/usr/bin/env python3
"""Largura de cada caractere na fonte do sistema do PSP (`.pgf`), P-93.

O RM3 desenha texto com `libfont.prx` (sceLibFont): os glifos vem da fonte do
firmware, `flash0:/font/jpn0.pgf`, que e' PROPORCIONAL no ASCII (um `i` ocupa
menos que um `M`). O PPSSPP traz uma copia em `assets/flash0/font/`.

So' le o que importa para medir largura: o avanco horizontal de cada glifo
(26.6 em ponto fixo, 64 = 1 pixel no tamanho nativo da fonte). Formato seguido
de `Core/Font/PGF.cpp` do PPSSPP: cabecalho, tabelas de dimensao / ajuste X /
ajuste Y / avanco (pares s32), mapa de sombra, [rev 3: dois mapas comprimidos],
charmap (charMapBpe bits por entrada), tabela de ponteiros de glifo
(charPointerBpe bits, em palavras de 4 B), e os glifos, lidos bit a bit LSB
primeiro.

Biblioteca:
  Fonte(caminho).avanco(ch) -> pixels (float), ou None se a fonte nao tem
  Fonte.largura(texto)       -> soma dos avancos

Linha de comando: pgf_largura.py <jpn0.pgf> [texto...]
"""
import sys, struct

FLAG_DIM, FLAG_BX, FLAG_BY, FLAG_ADV = 0x04, 0x08, 0x10, 0x20


class Bits:
    def __init__(self, b):
        self.b = b

    def get(self, n, pos):
        o = pos >> 3
        v = int.from_bytes(self.b[o:o + 8], 'little') >> (pos & 7)
        return v & ((1 << n) - 1)


class Fonte:
    def __init__(self, caminho):
        d = open(caminho, 'rb').read()
        self.d = d
        h_off, h_size = struct.unpack_from('<HH', d, 0)
        if d[4:8] != b'PGF0':
            raise ValueError('nao e PGF')
        rev, ver, cm_len, cp_len, cm_bpe, cp_bpe = struct.unpack_from('<6i', d, 8)
        self.rev = rev
        o = 32 + 2
        self.bpp = d[o]
        o = 36
        self.hsize, self.vsize, self.hres, self.vres = struct.unpack_from('<4i', d, o)
        o += 16 + 1 + 64 + 64 + 1
        self.first, self.last = struct.unpack_from('<HH', d, o)
        o += 4 + 26                    # pad5[26] -> 212: maxAscender
        o += 6 * 4 + 2 * 4 + 2 * 4 + 4 + 2   # metricas, maxGlyph, pad6 -> 258
        dim_n, xa_n, ya_n, adv_n = d[o], d[o + 1], d[o + 2], d[o + 3]
        o += 4 + 102                   # -> 364
        sh_len, sh_bpe = struct.unpack_from('<ii', d, o)
        rev3 = struct.unpack_from('<4i', d, 392) if rev == 3 else None   # logo depois do PGFHeader (392 B)
        p = h_size

        def tabela(n):
            nonlocal p
            t = [[], []]
            for _ in range(n):
                a, b = struct.unpack_from('<ii', d, p)
                t[0].append(a)
                t[1].append(b)
                p += 8
            return t
        self.dim = tabela(dim_n)
        self.xa = tabela(xa_n)
        self.ya = tabela(ya_n)
        self.adv = tabela(adv_n)
        p += ((sh_len * sh_bpe + 31) & ~31) // 8
        if rev == 3:
            p += rev3[1] * 4 + rev3[3] * 4
        cm = Bits(d[p:p + ((cm_len * cm_bpe + 31) & ~31) // 8])
        p += ((cm_len * cm_bpe + 31) & ~31) // 8
        cp = Bits(d[p:p + ((cp_len * cp_bpe + 31) & ~31) // 8])
        p += ((cp_len * cp_bpe + 31) & ~31) // 8
        self.glifos = Bits(d[p:])
        self.cm = [cm.get(cm_bpe, i * cm_bpe) for i in range(cm_len)]
        self.cp = [cp.get(cp_bpe, i * cp_bpe) for i in range(cp_len)]
        self._cache = {}

    def _glifo_avanco(self, gi):
        g = self.glifos
        pos = self.cp[gi] * 4 * 8
        pos += 14                      # tamanho do glifo (o PPSSPP pula)
        pos += 7 + 7 + 7 + 7           # w, h, left, top
        flags = g.get(6, pos)
        pos += 6 + 2 + 2 + 3 + 9       # flags, shadow flags (7 bits), shadow id
        pos += 8 if flags & FLAG_DIM == FLAG_DIM else 64
        pos += 8 if flags & FLAG_BX == FLAG_BX else 64
        pos += 8 if flags & FLAG_BY == FLAG_BY else 64
        if flags & FLAG_ADV == FLAG_ADV:
            return self.adv[0][g.get(8, pos)] / 64.0
        v = g.get(32, pos)
        return (v - (1 << 32) if v & 0x80000000 else v) / 64.0

    def avanco(self, ch):
        c = ord(ch)
        if c in self._cache:
            return self._cache[c]
        r = None
        if self.first <= c <= self.last and c - self.first < len(self.cm):
            gi = self.cm[c - self.first]
            if gi < len(self.cp):
                r = self._glifo_avanco(gi)
        self._cache[c] = r
        return r

    def largura(self, texto):
        return sum(self.avanco(c) or 0 for c in texto)


def main():
    f = Fonte(sys.argv[1])
    print('rev %d, glifos %d..%d (U+%04X..U+%04X), hSize %d'
          % (f.rev, f.first, f.last, f.first, f.last, f.hsize))
    for t in sys.argv[2:] or ['あ', '漢', 'i', 'M', 'W', ' ', 'Warrior', 'Martial Artist', 'ビショップ']:
        print('%-20s %7.2f px' % (t, f.largura(t)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

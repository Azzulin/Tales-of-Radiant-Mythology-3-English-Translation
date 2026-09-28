#!/usr/bin/env python3
"""Audita o campo `A` do indice do namco.bdi. SOMENTE LEITURA.

O P-14 registrou o campo A (bits 10..0 do primeiro u32 de cada registro do
indice) como "nao decifrado". Ele E' o padding da entrada:

    A = span - tamanho_exato_do_conteudo        =>   tamanho = span - A

Medido na ISO ORIGINAL, 7.344 entradas:
  * gzip   — `span - A` e' EXATAMENTE o fim do stream gzip, em 1.317 de 1.317;
  * EZBIND — `span - A` e' `max(data_off + size)` arredondado para cima no
             alinhamento do proprio EZBIND, e NUNCA e' menor que ele (0 de 4.938);
  * A < 2048 sempre, coerente com "padding menor que um setor".

Nenhuma ferramenta de build do projeto atualiza A. Quando o conteudo reinserido
cresce, o conteudo passa a terminar ALEM do tamanho declarado pelo indice —
invariante que a ISO original respeita em 100% das entradas.

IMPORTANTE, medido: isso **nao trunca** nada se o carregador ler por SETOR.
Como span e' multiplo de 2048 e A < 2048, `ceil((span-A)/2048)*2048 == span`
sempre; este script reporta a coluna `perde_por_setor`, que deu 0 em todas as
ISOs do projeto. E a entrada v=18 (`mev00_010.scr`, a primeira cena do jogo)
ja' viola o invariante na en18/en19 sem impedir o jogo de chegar a' guilda.
Ou seja: A desatualizado e' defeito de moldura real, mas nao e' truncamento.

Uso:
  bdi_campo_a.py <iso> [--lista] [--so-excedentes]
"""
import sys, os, zlib, argparse, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
from bdi_build_iso import ezbind_parse, alinhamento

SEC = 2048
LBA = 106896
GZ_MAGIC = b'\x1f\x8b\x08'


def fim_util(blob):
    """(fim do conteudo util, tipo, registros do EZBIND ou None)."""
    if blob[:3] == GZ_MAGIC:
        try:
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            d.decompress(blob)
            return len(blob) - len(d.unused_data), 'gzip', None
        except Exception:
            return None, 'gzip_ruim', None
    pe = ezbind_parse(blob)
    if pe:
        _, _, regs = pe
        return max(r[3] + r[2] for r in regs), 'ezbind', regs
    return None, 'outro', None


def a_esperado(span, fu, tipo, regs):
    """O valor que A teria num pacote feito como o do jogo."""
    if tipo == 'gzip':
        return span - fu
    al = alinhamento(regs)
    return span - ((fu + al - 1) // al) * al


def audita(caminho, lba=LBA):
    base = lba * SEC
    linhas = []
    with open(caminho, 'rb') as f:                  # nunca 'r+b'
        _, _, entries, _ = load_index(f, base)
        for e in entries:
            f.seek(base + e['off'])
            blob = f.read(e['span'])
            fu, tipo, regs = fim_util(blob)
            if fu is None:
                continue
            decl = e['span'] - e['A']
            ult = max(regs, key=lambda r: r[3])[0] if regs else '(gzip)'
            linhas.append({
                'v': e['v'], 'span': e['span'], 'A': e['A'], 'decl': decl,
                'fim_util': fu, 'excesso': fu - decl, 'tipo': tipo,
                'ultimo': ult, 'A_esperado': a_esperado(e['span'], fu, tipo, regs),
                'perde_por_setor': ((decl + SEC - 1) // SEC) * SEC < fu,
            })
    return linhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--lista', action='store_true', help='imprime uma linha por entrada')
    ap.add_argument('--so-excedentes', action='store_true')
    ap.add_argument('--lba', type=int, default=LBA)
    a = ap.parse_args()

    linhas = audita(a.iso, a.lba)
    exc = [l for l in linhas if l['excesso'] > 0]
    velho = [l for l in linhas if l['A'] != l['A_esperado']]
    perde = [l for l in linhas if l['perde_por_setor']]
    print('%s' % os.path.basename(a.iso))
    print('  entradas classificadas ........... %d' % len(linhas))
    print('  A desatualizado .................. %d' % len(velho))
    print('  conteudo ALEM de span-A .......... %d  (a original tem 0)' % len(exc))
    print('  perderia byte lendo por SETOR .... %d' % len(perde))
    if exc:
        pref = collections.Counter(l['ultimo'].rstrip('0123456789.arcsbin')[:6] for l in exc)
        print('  maior excesso .................... %+d B (v=%d, ultimo=%s)'
              % (max(l['excesso'] for l in exc),
                 max(exc, key=lambda l: l['excesso'])['v'],
                 max(exc, key=lambda l: l['excesso'])['ultimo']))
    if a.lista or a.so_excedentes:
        alvo = exc if a.so_excedentes else linhas
        print('\n%-6s %-9s %-6s %-9s %-9s %-8s %-8s %s'
              % ('v', 'span', 'A', 'decl', 'fim_util', 'excesso', 'A_certo', 'ultimo'))
        for l in sorted(alvo, key=lambda x: -x['excesso']):
            print('%-6d %-9d %-6d %-9d %-9d %+8d %-8d %s'
                  % (l['v'], l['span'], l['A'], l['decl'], l['fim_util'],
                     l['excesso'], l['A_esperado'], l['ultimo']))
    return 0


if __name__ == '__main__':
    sys.exit(main())

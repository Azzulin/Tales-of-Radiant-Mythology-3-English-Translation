#!/usr/bin/env python3
"""Inventario de strings de um ELF/PRX de PSP, com slot e tier. Ver P-39.

Responde, para cada string, as tres perguntas que decidem se ela e' traduzivel:

  1. **slot** — quantos bytes ha' de fato, contando o padding de alinhamento que
     ja era zero e mantendo um NUL antes da string seguinte. O orçamento e' o
     slot, NAO o comprimento do original (P-17 do dossie do RM2).
  2. **tier** — como o codigo alcanca a string:
       T1  ponteiro relocado com o valor == vaddr  -> repointavel, SEM limite
       T2  par lui/lo reconstruindo o vaddr        -> so in-place, orçamento = slot
       T3  nenhum dos dois                         -> so in-place, orçamento definitivo
     Antes de aceitar T3, os tres mecanismos tem de ter sido testados (P-18).
  3. **escrita in-place e' segura?** — a guarda correta para in-place NAO e' a do
     pool. Em in-place o endereco nao muda, e o par hi/lo apontando para a string
     e' a referencia do codigo a ela — rejeita-la pula o item em silencio, que foi
     o bug 6 do RM2. O que invalida in-place e':
       * a faixa passar do fim dos segmentos carregaveis
       * a faixa cobrir uma palavra relocada
       * um par hi/lo apontar para o INTERIOR da string (nao para o inicio)
       * a faixa cair dentro de blob embutido

Somente leitura.
"""
import struct, re
from collections import Counter
import prx

KANA = re.compile(rb'(?:\xa4[\xa1-\xf3]|\xa5[\xa1-\xf6])')
NUL = b'\x00'


def _valores_relocados(d, elf, rel):
    """vaddr apontado por cada palavra relocada de 32 bits -> lista de offsets."""
    alvo = {}
    for r in rel:
        if r['tipo'] != 2:                      # MIPS_32
            continue
        o = r['off_no_arquivo']
        if o + 4 > len(d):
            continue
        v = struct.unpack_from('<I', d, o)[0]
        alvo.setdefault(v, []).append(o)
    return alvo


def inventario(d, min_len=2, so_japones=False):
    elf = prx.ler(d)
    rel, origem = prx.relocacoes(d, elf)
    hilo = prx.pares_hilo(d, elf)
    fim = prx.fim_dos_carregaveis(elf)
    relocado_em = {r['off_no_arquivo'] for r in rel}
    palavras_relocadas = {o // 4 * 4 for o in relocado_em}
    ptr = _valores_relocados(d, elf, rel)

    # Nome da secao por faixa de vaddr, quando o modulo tem tabela de secoes.
    # NAO se pula segmento executavel: no PRX de PSP o segmento 0 costuma ser RWX
    # e carrega .text E .rodata juntos. Pular por flag foi um erro meu que
    # escondeu as strings inteiras — ver P-39.
    faixas = [(x['addr'], x['addr'] + x['size'], x.get('name', '?'))
              for x in elf['secs'] if x['addr'] and x['size']]

    def secao_de(va):
        for a, b, nm in faixas:
            if a <= va < b:
                return nm
        return '?'

    itens = []
    for s in prx.carregaveis(elf):
        ini, fimseg = s['off'], s['off'] + s['filesz']
        p = ini
        while p < fimseg:
            z = d.find(NUL, p, fimseg)
            if z < 0:
                break
            bruto = d[p:z]
            if len(bruto) >= min_len and all(32 <= c < 127 or c >= 0xa1 for c in bruto):
                # slot: consome os zeros seguintes, deixando um NUL
                q = z
                while q + 1 < fimseg and d[q + 1] == 0:
                    q += 1
                slot = q - p                     # bytes uteis, sem o NUL final
                va, seg = prx.vaddr_de_fileoff(elf, p)
                jp = bool(KANA.search(bruto))
                if so_japones and not jp:
                    p = q + 1
                    continue
                t1 = ptr.get(va, [])
                t2 = hilo.get(va, [])
                interior = [a for a in range(va + 1, va + len(bruto)) if a in hilo]
                cobre_reloc = any(w in palavras_relocadas
                                  for w in range(p // 4 * 4, q + 1, 4))
                tier = 'T1' if t1 else ('T2' if t2 else 'T3')
                itens.append({
                    'off': p, 'vaddr': va, 'seg': seg, 'secao': secao_de(va),
                    'bytes': len(bruto),
                    'slot': slot, 'folga': slot - len(bruto), 'jp': jp,
                    'tier': tier, 'ponteiros': len(t1), 'hilo': len(t2),
                    'hilo_interior': len(interior),
                    'inplace_ok': (q < fim) and not cobre_reloc and not interior,
                    'original': bruto,
                })
            p = (z + 1) if z >= p else p + 1
    return {'elf': elf, 'reloc': len(rel), 'reloc_origem': origem,
            'hilo': len(hilo), 'fim_carregaveis': fim, 'itens': itens}


def resumo(inv, secao=None):
    it = inv['itens']
    if secao:
        it = [x for x in it if x['secao'] == secao]
    jp = [x for x in it if x['jp']]
    return {
        'strings': len(it), 'japonesas': len(jp),
        'tiers': dict(Counter(x['tier'] for x in it)),
        'tiers_jp': dict(Counter(x['tier'] for x in jp)),
        'inplace_ok': sum(1 for x in it if x['inplace_ok']),
        'inplace_bloqueado': sum(1 for x in it if not x['inplace_ok']),
        'com_folga_de_padding': sum(1 for x in it if x['folga'] > 0),
        'folga_media': round(sum(x['folga'] for x in it) / max(1, len(it)), 2),
        'slot_min': min((x['slot'] for x in it), default=0),
        'slot_max': max((x['slot'] for x in it), default=0),
        'por_secao': dict(Counter(x['secao'] for x in it).most_common(8)),
    }

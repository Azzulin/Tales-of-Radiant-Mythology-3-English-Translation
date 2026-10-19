#!/usr/bin/env python3
"""Leitura de modulo ELF/PRX de PSP: segmentos, relocacao e pares hi/lo. Ver P-39.

Escrito para o EBOOT descriptografado, e **validado nos 153 modulos de
`battle_prx/`**, que sao ELF em texto claro da mesma arquitetura.

Cobre as duas formas em que a tabela de relocacao aparece:
  * secoes de tipo 0x700000A0 (`.rel.text`, `.rel.rodata`, ...) — o caso dos .prx
  * segmento de tipo 0x700000A0 (`PT_PRXRELOC`) — o caso provavel do EBOOT

**A armadilha do RM2 (P-14 do dossie):** `r_offset` e' relativo ao SEGMENTO indicado
em `(r_info >> 8) & 0xFF`, nao ao modulo. Tratar como relativo ao modulo produz
"nao ha relocacao" para ponteiros que comprovadamente existem.

Somente leitura. Nenhuma funcao deste modulo escreve em arquivo.
"""
import struct
from collections import Counter

SHT_PRXRELOC = 0x700000A0
PT_PRXRELOC = 0x700000A0
R_MIPS = {0: 'NONE', 1: 'MIPS_16', 2: 'MIPS_32', 3: 'MIPS_26',
          4: 'MIPS_HI16', 5: 'MIPS_LO16'}


def ler(d):
    """Devolve dict com header, segmentos e secoes."""
    if d[:4] != b'\x7fELF':
        raise ValueError(f'nao e ELF: {d[:8].hex()}')
    (e_type, e_machine) = struct.unpack_from('<HH', d, 0x10)
    e_entry, e_phoff, e_shoff = struct.unpack_from('<3I', d, 0x18)
    e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx = \
        struct.unpack_from('<5H', d, 0x2a)
    segs = []
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, p_off, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
            struct.unpack_from('<8I', d, o)
        segs.append({'i': i, 'type': p_type, 'off': p_off, 'vaddr': p_vaddr,
                     'filesz': p_filesz, 'memsz': p_memsz, 'flags': p_flags,
                     'align': p_align})
    secs = []
    if e_shoff and e_shnum:
        for i in range(e_shnum):
            o = e_shoff + i * e_shentsize
            nm, typ, fl, addr, off, size, link, info, al, ent = \
                struct.unpack_from('<10I', d, o)
            secs.append({'i': i, 'name_off': nm, 'type': typ, 'addr': addr,
                         'off': off, 'size': size, 'entsize': ent})
        st = secs[e_shstrndx]
        for s in secs:
            a = st['off'] + s['name_off']
            z = d.find(b'\x00', a)
            s['name'] = d[a:z].decode('latin1')
    return {'type': e_type, 'machine': e_machine, 'entry': e_entry,
            'segs': segs, 'secs': secs}


def carregaveis(elf):
    return [s for s in elf['segs'] if s['type'] == 1]


def vaddr_de_fileoff(elf, off):
    for s in carregaveis(elf):
        if s['off'] <= off < s['off'] + s['filesz']:
            return s['vaddr'] + (off - s['off']), s['i']
    return None, None


def fileoff_de_vaddr(elf, va):
    for s in carregaveis(elf):
        if s['vaddr'] <= va < s['vaddr'] + s['filesz']:
            return s['off'] + (va - s['vaddr']), s['i']
    return None, None


def fim_dos_carregaveis(elf):
    """A fronteira entre 'pode escrever' e 'crash' (classe 1 do RM2)."""
    return max((s['off'] + s['filesz']) for s in carregaveis(elf))


def relocacoes(d, elf):
    """Devolve (lista, origem). Cada item: dict com off_no_arquivo, tipo,
    seg_base, seg_addend. `off_no_arquivo` ja resolve o r_offset relativo ao
    segmento — que e' o erro do P-14 do RM2."""
    blocos = [(s['off'], s['size'], 'secao ' + s.get('name', '?'))
              for s in elf['secs'] if s['type'] == SHT_PRXRELOC and s['size']]
    if not blocos:
        blocos = [(s['off'], s['filesz'], f'segmento PT_PRXRELOC #{s["i"]}')
                  for s in elf['segs'] if s['type'] == PT_PRXRELOC and s['filesz']]
    saida = []
    origem = []
    carreg = carregaveis(elf)
    for off, size, rot in blocos:
        origem.append(f'{rot} ({size // 8} entradas)')
        for i in range(size // 8):
            r_off, r_info = struct.unpack_from('<II', d, off + i * 8)
            tipo = r_info & 0xFF
            seg_base = (r_info >> 8) & 0xFF
            seg_add = (r_info >> 16) & 0xFF
            if seg_base >= len(carreg):
                continue
            base = carreg[seg_base]
            saida.append({'off_no_arquivo': base['off'] + r_off,
                          'r_offset': r_off, 'tipo': tipo,
                          'seg_base': seg_base, 'seg_addend': seg_add})
    return saida, origem


# ---------------- pares hi/lo do MIPS ----------------
# lui rX, imm            opcode 0x0f
# addiu rY, rX, imm      opcode 0x09     ori 0x0d
# lw/sw/lb/lbu/lh/lhu/sb/sh com base rX  opcodes 0x23 0x2b 0x20 0x24 0x21 0x25 0x28 0x29
OPS_LO = {0x09, 0x0d, 0x23, 0x2b, 0x20, 0x24, 0x21, 0x25, 0x28, 0x29}


def pares_hilo(d, elf, janela=64):
    """Reconstroi endereco de par lui/lo. Devolve dict endereco -> lista de
    (off_do_lui, off_do_lo). Percorre so os segmentos carregaveis executaveis."""
    res = {}
    for s in carregaveis(elf):
        if not (s['flags'] & 0x1):          # PF_X
            continue
        base, n = s['off'], s['filesz'] & ~3
        pend = {}
        for p in range(0, n, 4):
            w = struct.unpack_from('<I', d, base + p)[0]
            op = w >> 26
            if op == 0x0f:                   # lui rt, imm
                rt = (w >> 16) & 0x1F
                pend[rt] = (w & 0xFFFF, p)
                continue
            if op in OPS_LO:
                rs = (w >> 21) & 0x1F
                if rs in pend:
                    hi, ppos = pend[rs]
                    if p - ppos <= janela:
                        lo = w & 0xFFFF
                        if lo >= 0x8000:
                            lo -= 0x10000
                        addr = ((hi << 16) + lo) & 0xFFFFFFFF
                        res.setdefault(addr, []).append((base + ppos, base + p))
    return res


def resumo(d, rot=''):
    """Relatorio de uma linha por fato. Usado para validar o parser."""
    elf = ler(d)
    carreg = carregaveis(elf)
    rel, origem = relocacoes(d, elf)
    hilo = pares_hilo(d, elf)
    fim = fim_dos_carregaveis(elf)
    delta = {s['off'] - s['vaddr'] for s in carreg}
    dentro = sum(1 for r in rel if r['off_no_arquivo'] < fim)
    hl_dentro = sum(1 for a in hilo if fileoff_de_vaddr(elf, a)[0] is not None)
    return {'rot': rot, 'tam': len(d), 'segs': len(elf['segs']),
            'carregaveis': len(carreg), 'secoes': len(elf['secs']),
            'fim_carregaveis': fim, 'delta_off_menos_vaddr': sorted(delta),
            'reloc': len(rel), 'reloc_origem': origem,
            'reloc_dentro_dos_carregaveis': dentro,
            'reloc_tipos': dict(Counter(R_MIPS.get(r['tipo'], r['tipo']) for r in rel)),
            'hilo_enderecos': len(hilo),
            'hilo_dentro_do_modulo': hl_dentro}

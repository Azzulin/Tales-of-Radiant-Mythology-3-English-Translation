#!/usr/bin/env python3
"""Le um PRX de PSP em ELF texto claro: secoes, nome do modulo e bibliotecas
importadas/exportadas (`.lib.stub` / `.lib.ent`). Somente leitura.

Uso: prx_info.py <arquivo.prx> [...]
"""
import sys, struct


def secoes(d):
    shoff, shentsize, shnum, shstrndx = struct.unpack_from('<I', d, 0x20)[0], \
        struct.unpack_from('<H', d, 0x2e)[0], struct.unpack_from('<H', d, 0x30)[0], \
        struct.unpack_from('<H', d, 0x32)[0]
    hdrs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        name, typ, flags, addr, off, size, link, info, align, entsz = \
            struct.unpack_from('<10I', d, o)
        hdrs.append({'name_off': name, 'type': typ, 'addr': addr, 'off': off, 'size': size})
    strtab = hdrs[shstrndx]
    for h in hdrs:
        a = strtab['off'] + h['name_off']
        z = d.find(b'\x00', a)
        h['name'] = d[a:z].decode('latin1')
    return hdrs


def vaddr_to_off(hdrs, va):
    for h in hdrs:
        if h['addr'] and h['addr'] <= va < h['addr'] + h['size']:
            return h['off'] + (va - h['addr'])
    return None


def cstr(d, off):
    if off is None or off >= len(d):
        return None
    z = d.find(b'\x00', off)
    return d[off:z].decode('latin1', 'replace')


def main():
    for p in sys.argv[1:]:
        d = open(p, 'rb').read()
        print(f'===== {p} ({len(d)} B) =====')
        if d[:4] != b'\x7fELF':
            print(f'  nao e ELF em texto claro: {d[:8].hex()}')
            continue
        hdrs = secoes(d)
        print('  secoes:', ', '.join(f'{h["name"]}({h["size"]})' for h in hdrs if h['name']))
        for sec, rot, passo in (('.lib.stub', 'IMPORTA', 0x14), ('.lib.ent', 'EXPORTA', 0x10)):
            h = next((x for x in hdrs if x['name'] == sec), None)
            if not h or not h['size']:
                continue
            print(f'  --- {rot} ({sec}, {h["size"]} B) ---')
            o = h['off']
            fim = h['off'] + h['size']
            while o + passo <= fim:
                name_va = struct.unpack_from('<I', d, o)[0]
                entsize = d[o + 8]
                nvar = d[o + 9]
                nfunc = struct.unpack_from('<H', d, o + 10)[0]
                nome = cstr(d, vaddr_to_off(hdrs, name_va)) or f'@{name_va:#x}'
                print(f'      {nome:<28} funcs={nfunc:<4} vars={nvar}')
                o += (entsize * 4) if entsize else passo


if __name__ == '__main__':
    main()

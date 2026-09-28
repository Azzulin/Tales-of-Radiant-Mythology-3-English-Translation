#!/usr/bin/env python3
"""Leitor ISO9660 somente-leitura: lista arvore e extrai um arquivo.
Uso: iso_ls.py <iso> [--tree] [--extract /CAMINHO/ARQ saida]
Nunca escreve na ISO.
"""
import sys, struct

SEC = 2048

class Iso:
    def __init__(self, path):
        self.f = open(path, 'rb')  # somente leitura
        self.f.seek(16*SEC)
        pvd = self.f.read(SEC)
        assert pvd[1:6] == b'CD001', 'PVD invalido'
        self.volid = pvd[40:72].decode('latin1').strip()
        root = pvd[156:190]
        self.root_lba = struct.unpack_from('<I', root, 2)[0]
        self.root_len = struct.unpack_from('<I', root, 10)[0]

    def read_dir(self, lba, length):
        self.f.seek(lba*SEC)
        data = self.f.read(length)
        out, i = [], 0
        while i < len(data):
            rl = data[i]
            if rl == 0:
                i = (i//SEC + 1)*SEC
                continue
            rec = data[i:i+rl]
            ext_lba = struct.unpack_from('<I', rec, 2)[0]
            size = struct.unpack_from('<I', rec, 10)[0]
            flags = rec[25]
            nlen = rec[32]
            name = rec[33:33+nlen]
            if name in (b'\x00', b'\x01'):
                nm = '.' if name == b'\x00' else '..'
            else:
                nm = name.decode('latin1').split(';')[0]
            out.append((nm, ext_lba, size, bool(flags & 2)))
            i += rl
        return out

    def walk(self, lba=None, length=None, prefix=''):
        if lba is None:
            lba, length = self.root_lba, self.root_len
        for nm, elba, size, isdir in self.read_dir(lba, length):
            if nm in ('.', '..'):
                continue
            p = prefix + '/' + nm
            if isdir:
                yield (p, elba, size, True)
                yield from self.walk(elba, size, p)
            else:
                yield (p, elba, size, False)

    def find(self, target):
        for p, lba, size, isdir in self.walk():
            if p.upper() == target.upper():
                return (p, lba, size, isdir)
        return None

    def extract(self, target, dest):
        r = self.find(target)
        if not r:
            raise SystemExit('nao encontrado: ' + target)
        _, lba, size, _ = r
        self.f.seek(lba*SEC)
        with open(dest, 'wb') as o:
            left = size
            while left > 0:
                chunk = self.f.read(min(1 << 20, left))
                if not chunk:
                    break
                o.write(chunk)
                left -= len(chunk)
        print(f'extraido {target} lba={lba} size={size} -> {dest}')

if __name__ == '__main__':
    iso = Iso(sys.argv[1])
    print('volid:', repr(iso.volid), 'root_lba:', iso.root_lba, 'root_len:', iso.root_len)
    if '--extract' in sys.argv:
        k = sys.argv.index('--extract')
        iso.extract(sys.argv[k+1], sys.argv[k+2])
    else:
        n = 0
        tot = 0
        for p, lba, size, isdir in iso.walk():
            n += 1
            if not isdir:
                tot += size
            if '--tree' in sys.argv:
                print(f'{"D" if isdir else "F"} {lba:9d} {size:10d} {p}')
        print(f'entradas={n} bytes_arquivos={tot}')

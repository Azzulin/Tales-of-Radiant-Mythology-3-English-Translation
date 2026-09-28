#!/usr/bin/env python3
"""Lista o indice do namco.bdi (lido de dentro da ISO, somente leitura).

Estrutura assumida (ver PADROES_DESCOBERTOS.md P-08):
  0x0000  u16[16384]  tabela hash: valor v = indice de registro (0 = vazio)
  0x8000  u32         desconhecido (0)
  0x8004  base do vetor de registros; registro v em 0x8004 + v*8
          registro = (u32 off31|flag_bit31, u32 chave)
          v = 0 e v = 1 sao dummies; entradas reais em v = 2 .. 2+count-1
          registro seguinte a ultima entrada tem off = tamanho do bdi (sentinela)
  count   u32 em 0x8004

Uso:
  bdi_ls.py <iso> <lba> <size> [--magic] [--csv saida.csv]
"""
import sys, struct, csv

SEC = 2048
HASH_BYTES = 0x8000
REC_BASE = 0x8004


def load_index(f, base):
    f.seek(base)
    head = f.read(HASH_BYTES + 16)
    buckets = struct.unpack_from('<16384H', head, 0)
    count = struct.unpack_from('<I', head, REC_BASE)[0]
    first_v, last_v = 2, 2 + count - 1
    need = REC_BASE + (last_v + 2) * 8
    f.seek(base)
    raw = f.read(need)
    recs = []
    for v in range(first_v, last_v + 2):          # +1 registro = sentinela
        a, key = struct.unpack_from('<II', raw, REC_BASE + v * 8)
        recs.append((v, a & 0x7FFFFFFF, a >> 31, key))
    entries = []
    for i in range(len(recs) - 1):
        v, off, flag, key = recs[i]
        nxt = recs[i + 1][1]
        entries.append({'v': v, 'off': off, 'size': nxt - off, 'flag': flag, 'key': key})
    return buckets, count, entries, recs[-1][1]


def main():
    iso, lba, size = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    base = lba * SEC
    with open(iso, 'rb') as f:                    # somente leitura
        buckets, count, entries, sentinel = load_index(f, base)

        print(f'count={count}  entradas={len(entries)}  sentinela=0x{sentinel:x} ({sentinel})')
        print(f'bdi size={size}  sentinela == size ? {sentinel == size}')
        nz = [v for v in buckets if v]
        print(f'buckets nao-zero={len(nz)}  distintos={len(set(nz))}  '
              f'min={min(nz)} max={max(nz)}')
        offs = [e['off'] for e in entries]
        print(f'offsets ordenados? {all(offs[i] <= offs[i+1] for i in range(len(offs)-1))}')
        print(f'todos dentro do arquivo? {max(e["off"]+e["size"] for e in entries) <= size}')
        neg = [e for e in entries if e['size'] < 0]
        zero = [e for e in entries if e['size'] == 0]
        print(f'tamanhos negativos={len(neg)}  tamanhos zero={len(zero)}')
        print(f'flag bit31: setado em {sum(e["flag"] for e in entries)} de {len(entries)}')
        print(f'soma dos tamanhos={sum(e["size"] for e in entries)}  '
              f'primeiro off=0x{offs[0]:x}  ultimo fim=0x{entries[-1]["off"]+entries[-1]["size"]:x}')

        if '--magic' in sys.argv:
            from collections import Counter
            mag = Counter()
            for e in entries:
                if e['size'] <= 0:
                    mag['(vazio)'] += 1
                    continue
                f.seek(base + e['off'])
                head = f.read(min(16, e['size']))
                e['head'] = head
                k = head[:4]
                pr = ''.join(chr(b) if 32 <= b < 127 else '.' for b in k)
                mag[f'{k.hex()}  {pr}'] += 1
            print('--- magics (4 primeiros bytes) ---')
            for k, c in mag.most_common(30):
                print(f'{c:6d}  {k}')

        if '--csv' in sys.argv:
            out = sys.argv[sys.argv.index('--csv') + 1]
            with open(out, 'w', newline='') as o:
                w = csv.writer(o)
                w.writerow(['v', 'off', 'size', 'flag', 'key', 'head16'])
                for e in entries:
                    w.writerow([e['v'], e['off'], e['size'], e['flag'],
                                f'{e["key"]:08x}', e.get('head', b'').hex()])
            print(f'csv -> {out}')


if __name__ == '__main__':
    main()

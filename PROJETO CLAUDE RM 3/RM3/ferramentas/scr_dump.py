#!/usr/bin/env python3
"""Dumpa todas as cenas FaceChat (.scr) do namco.bdi para a tabela de strings.

Uso: scr_dump.py <iso> <lba> <size> <catalogo.csv> <saida.csv>

Le direto da ISO (somente leitura) usando os offsets do catalogo — nao extrai
arquivo nenhum para o disco.

Valida, por cena: gzip, magic FaceChat, offset[0]==0, offsets crescentes,
terminador de cada string, decodificacao EUC-JP e **round-trip byte-perfeito**.
Cena que falhar qualquer checagem e' recusada inteira e listada no relatorio.
"""
import sys, csv, gzip, struct, io
import facechat

SEC = 2048


def main():
    iso, lba, size, cat, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
    base = lba * SEC
    rows = [r for r in csv.DictReader(open(cat, encoding='utf-8'))
            if r['nome'].lower().endswith('.scr')]
    print(f'{len(rows)} .scr no catalogo')
    ok = rec = 0
    bad = []
    tot_bytes = 0
    with open(iso, 'rb') as f, open(out, 'w', newline='', encoding='utf-8') as o:
        w = csv.writer(o)
        w.writerow(['id', 'arquivo', 'offset', 'bytes_max', 'original', 'traducao',
                    'bytes_usados', 'control_codes', 'status', 'nota'])
        for r in rows:
            nome, sz, off, v = r['nome'], int(r['tamanho']), int(r['off_bdi']), r['entrada_v']
            f.seek(base + off)
            raw = f.read(sz)
            try:
                d = gzip.decompress(raw)
                if not facechat.round_trip_ok(d):
                    raise ValueError('round-trip falhou')
                pr = facechat.parse(d)
            except Exception as e:
                bad.append((v, nome, str(e)[:60])); continue
            ok += 1
            for i, s in enumerate(pr['strings']):
                try:
                    txt = s.decode(facechat.ENC)
                except UnicodeDecodeError as e:
                    bad.append((v, f'{nome}#{i}', f'euc_jp: {e}')); continue
                cc = []
                if b'\r\n' in s: cc.append('CRLF')
                if b'\n' in s.replace(b'\r\n', b''): cc.append('LF')
                w.writerow([f'{v}:{nome}:{i}', f'{nome} (v{v})', i, len(s), txt, '',
                            0, '|'.join(cc), 'pendente', 'FaceChat: sem limite de bytes'])
                rec += 1
                tot_bytes += len(s)
    print(f'cenas ok={ok} recusadas={len(rows)-ok}')
    print(f'strings={rec}  bytes de texto japones={tot_bytes}')
    if bad:
        print(f'RECUSADOS ({len(bad)}):')
        for b in bad[:15]: print('  ', b)


if __name__ == '__main__':
    main()

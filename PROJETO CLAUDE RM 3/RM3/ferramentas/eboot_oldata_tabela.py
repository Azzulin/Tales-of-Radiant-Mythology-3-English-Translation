#!/usr/bin/env python3
"""Sincroniza com o `v2070` a COPIA da tabela de episodios que o EBOOT carrega (P-86).

A tela de Sinopse nao le o cabecalho nem os registros do `oldata.bin`
(`generic/oldata.bin.gz`, entrada `v2070`). A rotina em `0x08A04184` percorre
uma tabela FIXA no EBOOT, em `0x08CF2F08`, com 52 registros (A, B, C) de 12 B e
um registro final (A, total dos titulos, total da narracao). Para cada episodio:

    titulo   = arquivo[636  + B[i] : 636  + B[i+1]]      addiu a1,a1,636  em 0x08A04274
    narracao = arquivo[1383 + C[i] : 1383 + C[i+1]]      addiu a1,a1,1383 em 0x08A042C4

com `malloc(tamanho + 1)` para cada um. A tabela do EBOOT original e' copia exata
dos registros do `v2070` original. Qualquer mudanca de tamanho no texto exige
reescrever a tabela e o 1383 (o offset da narracao). O 636 (cabecalho de 12 B +
52 x 12) nao muda. O campo A (limiar de progresso, lido tambem em `0x08A21D10`)
fica como esta'.

Opera sobre a ISO final, no `EBOOT.BIN` decifrado que ela carrega, calculando a
tabela a partir do `v2070` da MESMA ISO, para que os dois nunca fiquem fora de
sincronia. Confere antes de escrever que a tabela e as instrucoes sao as do
EBOOT original (ou ja' as corretas: a ferramenta e' idempotente).

Uso:
  eboot_oldata_tabela.py <iso> [--aplicar]
"""
import sys, os, gzip, struct, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index
import oldata, iso_ls

SEC = 2048
LBA_BDI = 106896
V_OLDATA = 2070
N_EP = 52
# enderecos no EBOOT decifrado, medidos com prx.fileoff_de_vaddr (P-86)
TABELA_FOFF = 0x4EFF08          # vaddr 0x08CF2F08
INSTR_TIT_FOFF = 0x201274       # vaddr 0x08A04274: addiu a1,a1,636
INSTR_NAR_FOFF = 0x2012C4       # vaddr 0x08A042C4: addiu a1,a1,1383
ADDIU_A1_A1 = 0x24A50000
TABELA_ORIGINAL_SENTINELA = (27000, 747, 42169)
OFF_TITULOS = 636


def tabela_de(raw):
    p = oldata.parse(raw)
    count, off_tit, off_nar, tam_cab = oldata.cabecalho(raw)
    if count != N_EP or off_tit != OFF_TITULOS:
        raise ValueError('v2070 com count=%d off_titulos=%d; esperado %d e %d'
                         % (count, off_tit, N_EP, OFF_TITULOS))
    if off_nar > 0x7FFF:
        raise ValueError('off_narracao %d nao cabe no imediato de 16 bits' % off_nar)
    tot_tit = off_nar - off_tit
    tot_nar = sum(len(l) + 1 for l in p['narracao'])
    # B sai dos proprios titulos (P-86), nao do campo do arquivo, que um build
    # antigo pode ter deixado velho; C sai do arquivo (e' a fronteira de episodio
    # que o build decidiu) e e' conferido abaixo
    bs_calc, pos = [], 0
    for t in p['titulos']:
        bs_calc.append(pos)
        pos += len(t) + 1
    velhos = sum(1 for r, b in zip(p['recs'], bs_calc) if r[1] != b)
    if velhos:
        print('aviso: %d campos B do arquivo estavam desatualizados; usando os calculados' % velhos)
    recs = [(r[0], b, r[2]) for r, b in zip(p['recs'], bs_calc)]
    # confere: B/C crescentes e dentro do arquivo
    bs = [r[1] for r in recs] + [tot_tit]
    cs = [r[2] for r in recs] + [tot_nar]
    if any(b <= a for a, b in zip(bs, bs[1:])) or any(b <= a for a, b in zip(cs, cs[1:])):
        raise ValueError('B ou C fora de ordem no v2070 — rode o build com as guardas do P-83/P-86')
    if off_nar + tot_nar > len(raw):
        raise ValueError('narracao passa do fim do arquivo')
    sent = (TABELA_ORIGINAL_SENTINELA[0], tot_tit, tot_nar)
    dado = b''.join(struct.pack('<3I', *r) for r in recs + [sent])
    return dado, off_nar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    if 'Caravan.iso' in os.path.basename(a.iso):
        print('RECUSADO: isto parece a ISO original')
        return 1

    I = iso_ls.Iso(a.iso)
    achou = I.find('/PSP_GAME/SYSDIR/EBOOT.BIN')
    if not achou:
        print('RECUSADO: EBOOT.BIN nao encontrado')
        return 1
    _, lba_eb, tam_eb, _ = achou
    I.f.close()
    base_eb = lba_eb * SEC

    with open(a.iso, 'rb') as f:
        e = {x['v']: x for x in load_index(f, LBA_BDI * SEC)[2]}[V_OLDATA]
        f.seek(LBA_BDI * SEC + e['off'])
        blob = f.read(e['span'])
        raw = gzip.decompress(blob) if blob[:3] == b'\x1f\x8b\x08' else blob
        f.seek(base_eb)
        if f.read(4) != b'\x7fELF':
            print('RECUSADO: o EBOOT.BIN da ISO nao e o ELF decifrado')
            return 1
        f.seek(base_eb + TABELA_FOFF)
        tab_atual = f.read((N_EP + 1) * 12)
        f.seek(base_eb + INSTR_TIT_FOFF)
        w_tit = struct.unpack('<I', f.read(4))[0]
        f.seek(base_eb + INSTR_NAR_FOFF)
        w_nar = struct.unpack('<I', f.read(4))[0]

    nova, off_nar = tabela_de(raw)
    if w_tit != ADDIU_A1_A1 | OFF_TITULOS:
        print('RECUSADO: instrucao em 0x08A04274 e %08x, esperado addiu a1,a1,636' % w_tit)
        return 1
    if w_nar >> 16 != ADDIU_A1_A1 >> 16:
        print('RECUSADO: instrucao em 0x08A042C4 e %08x, esperado addiu a1,a1,imm' % w_nar)
        return 1
    ultimo = struct.unpack_from('<3I', tab_atual, N_EP * 12)
    ja_feito = tab_atual == nova and (w_nar & 0xFFFF) == off_nar
    original = ultimo == TABELA_ORIGINAL_SENTINELA and (w_nar & 0xFFFF) == 1383
    if not (ja_feito or original):
        print('RECUSADO: a tabela do EBOOT nao e nem a original nem a esperada '
              '(sentinela %s, imediato %d)' % (ultimo, w_nar & 0xFFFF))
        return 1
    difs = sum(1 for i in range(N_EP + 1) if tab_atual[i * 12:i * 12 + 12] != nova[i * 12:i * 12 + 12])
    print('EBOOT.BIN no LBA %d; v2070 com %d B descomprimido' % (lba_eb, len(raw)))
    print('tabela: %d de %d registros mudam; off_narracao %d -> %d; sentinela -> %s'
          % (difs, N_EP + 1, w_nar & 0xFFFF, off_nar, struct.unpack_from('<3I', nova, N_EP * 12)))
    if ja_feito:
        print('ja sincronizado. Nada a fazer.')
        return 0
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    with open(a.iso, 'r+b') as f:
        f.seek(base_eb + TABELA_FOFF)
        f.write(nova)
        f.seek(base_eb + INSTR_NAR_FOFF)
        f.write(struct.pack('<I', ADDIU_A1_A1 | off_nar))
    with open(a.iso, 'rb') as f:
        f.seek(base_eb + TABELA_FOFF)
        ok = f.read(len(nova)) == nova
        f.seek(base_eb + INSTR_NAR_FOFF)
        ok = ok and struct.unpack('<I', f.read(4))[0] == ADDIU_A1_A1 | off_nar
    if not ok:
        print('FALHOU a releitura')
        return 2
    print('escrito e relido.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

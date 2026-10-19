#!/usr/bin/env python3
"""Troca o EBOOT.BIN de uma COPIA da ISO por um de tamanho diferente (P-91).

O `iso_troca_eboot.py` exige tamanho identico de proposito: crescer o arquivo no
lugar pisaria no vizinho (`UPDATE/PARAM.SFO` comeca 1 setor depois). Com o
segmento de transbordo o EBOOT cresce, entao esta ferramenta:

  1. le a arvore ISO 9660 inteira e a posicao de cada registro de diretorio;
  2. se o EBOOT novo cabe na extensao atual (em setores), grava no lugar;
     senao procura o primeiro buraco entre arquivos (first-fit, so' setores
     que nenhum arquivo ou diretorio usa) e confere que ele e' TODO zero;
  3. grava o EBOOT la, zera a extensao antiga, e reescreve extent e tamanho
     do registro `SYSDIR/EBOOT.BIN` (campos LE e BE, ISO 9660 9.1.3/9.1.4);
  4. rele pela arvore e confere byte a byte; confere que nenhum outro arquivo
     mudou de extent/tamanho e que o tamanho da ISO nao mudou.

Na ISO do RM3 o buraco usado e' `20288..56176` (73,5 MB de zeros entre
`UPDATE/DATA.BIN` e `PARAM.SFO`). A tabela de caminhos (path table) so' lista
diretorios: nao muda. Tamanho igual ao atual -> e' a troca de sempre, no lugar.

DRY-RUN por padrao. Recusa a ISO original pelo nome.

Uso:
  iso_eboot_realoca.py <copia.iso> <eboot_novo> [--aplicar]
"""
import sys, os, struct, hashlib, argparse

SEC = 2048
PROIBIDO = 'Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso'
ALVO = '/PSP_GAME/SYSDIR/EBOOT.BIN'


def arvore(f):
    """[(caminho, lba, tamanho, eh_dir, offset_do_registro)]"""
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    assert pvd[1:6] == b'CD001', 'PVD invalido'
    root = pvd[156:190]
    out = []

    def anda(lba, n, prefixo):
        f.seek(lba * SEC)
        d = f.read(n)
        i = 0
        while i < len(d):
            rl = d[i]
            if rl == 0:
                i = (i // SEC + 1) * SEC
                continue
            r = d[i:i + rl]
            ext, tam, fl = struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0], r[25]
            nome = r[33:33 + r[32]]
            if nome not in (b'\x00', b'\x01'):
                p = prefixo + '/' + nome.decode('latin1').split(';')[0]
                out.append((p, ext, tam, bool(fl & 2), lba * SEC + i))
                if fl & 2:
                    anda(ext, tam, p)
            i += rl

    out.append(('/', struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], True, None))
    anda(out[0][1], out[0][2], '')
    vss = struct.unpack_from('<I', pvd, 80)[0]
    return out, vss


def setores(tam):
    return -(-tam // SEC)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('eboot')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    if os.path.basename(a.iso) == PROIBIDO:
        print('RECUSADO: %s e a ISO ORIGINAL. Trabalhe em copia.' % a.iso)
        return 1
    novo = open(a.eboot, 'rb').read()
    if novo[:4] != b'\x7fELF':
        print('RECUSADO: o EBOOT novo nao e ELF')
        return 1
    tam_iso = os.path.getsize(a.iso)

    with open(a.iso, 'rb') as f:
        arv, vss = arvore(f)
        ent = [x for x in arv if x[0].upper() == ALVO]
        if len(ent) != 1:
            print('RECUSADO: %s nao encontrado (ou duplicado)' % ALVO)
            return 1
        _, lba0, tam0, _, pos_reg = ent[0]
        f.seek(pos_reg)
        reg = f.read(34)
        ns0, ns = setores(tam0), setores(len(novo))
        print('EBOOT atual: LBA %d, %d B (%d setores) | novo: %d B (%d setores) sha256=%s'
              % (lba0, tam0, ns0, len(novo), ns, hashlib.sha256(novo).hexdigest()[:16]))

        if ns <= ns0:
            lba = lba0
            print('cabe na extensao atual: grava no lugar')
        else:
            # a extensao antiga conta como ocupada: so' e' zerada depois da gravacao
            usado = sorted((x[1], x[1] + max(1, setores(x[2]))) for x in arv)
            usado.append((0, 16 + 2))       # area de sistema + PVD/terminador
            usado.sort()
            lba, cursor = None, 0
            for ini, fim in usado:
                if ini - cursor >= ns:
                    lba = cursor
                    break
                cursor = max(cursor, fim)
            if lba is None and vss - cursor >= ns:
                lba = cursor
            if lba is None:
                print('RECUSADO: nenhum buraco de %d setores livre na ISO' % ns)
                return 1
            # o buraco fica alinhado a 16 setores, como os arquivos da ISO
            lba = -(-lba // 16) * 16
            if any(lba < fim and ini < lba + ns for ini, fim in usado) or lba + ns > vss:
                print('RECUSADO: o buraco alinhado nao cabe')
                return 1
            f.seek(lba * SEC)
            if f.read(ns * SEC).count(0) != ns * SEC:
                print('RECUSADO: o buraco LBA %d..%d nao e todo zero' % (lba, lba + ns))
                return 1
            print('nao cabe no lugar: buraco livre e zerado em LBA %d..%d' % (lba, lba + ns))

    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    with open(a.iso, 'r+b') as f:
        if lba != lba0:
            f.seek(lba0 * SEC)
            f.write(b'\x00' * (ns0 * SEC))
        f.seek(lba * SEC)
        f.write(novo + b'\x00' * (ns * SEC - len(novo)))
        r = bytearray(reg)
        struct.pack_into('<I', r, 2, lba)
        struct.pack_into('>I', r, 6, lba)
        struct.pack_into('<I', r, 10, len(novo))
        struct.pack_into('>I', r, 14, len(novo))
        f.seek(pos_reg)
        f.write(r)
        f.flush()
        os.fsync(f.fileno())

    # releitura pela arvore
    with open(a.iso, 'rb') as f:
        arv2, vss2 = arvore(f)
        e2 = [x for x in arv2 if x[0].upper() == ALVO][0]
        f.seek(e2[1] * SEC)
        lido = f.read(e2[2])
    falhas = []
    if (e2[1], e2[2]) != (lba, len(novo)) or lido != novo:
        falhas.append('EBOOT relido nao confere')
    antes = {x[0]: x[1:4] for x in arv if x[0] != ent[0][0]}
    depois = {x[0]: x[1:4] for x in arv2 if x[0] != ent[0][0]}
    if antes != depois:
        falhas.append('outro arquivo mudou de extent/tamanho')
    if vss2 != vss or os.path.getsize(a.iso) != tam_iso:
        falhas.append('tamanho da ISO mudou')
    if falhas:
        print('FALHOU: ' + '; '.join(falhas))
        return 2
    print('gravado e conferido: EBOOT em LBA %d, %d B; demais %d entradas intactas; ISO %d B'
          % (lba, len(novo), len(depois), tam_iso))
    return 0


if __name__ == '__main__':
    sys.exit(main())

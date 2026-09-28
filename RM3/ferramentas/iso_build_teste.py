#!/usr/bin/env python3
"""Gera uma ISO de teste com TODAS as frentes traduzidas atuais — EBOOT + dialogo.
Ver P-53.

Uso:
  py iso_build_teste.py <iso_saida> [--aplicar] [--eboot ARQ] [--forcar]

Existe porque `bdi_build_iso.py` (dialogo) e `iso_troca_eboot.py` (EBOOT) sao
duas ferramentas separadas que escrevem em regioes diferentes da MESMA ISO, e
rodar so' uma delas por engano gera uma ISO de teste que RETROCEDE uma frente
que ja estava pronta — foi exatamente o que aconteceu em 11/09/2026: a tela de
criacao de personagem (ja traduzida e validada no `en03`) voltou para japones
porque o build daquela sessao rodou so' `bdi_build_iso.py`, que parte da ISO
ORIGINAL (com o EBOOT japones) e nunca soube que existia um EBOOT traduzido
para preservar.

Este script e' o UNICO caminho recomendado para gerar uma ISO de teste: ele
SEMPRE aplica as duas frentes na mesma rodada, na ordem
  1. dialogo   (bdi_build_iso.py, a partir da ISO original + RM3/lotes/)
  2. EBOOT     (iso_troca_eboot.py, o build enNN mais alto em RM3/eboot/,
                a nao ser que --eboot aponte outro arquivo)
de modo que "esqueci a outra frente" deixe de ser possivel.

DRY-RUN por padrao (delega o dry-run de cada etapa as ferramentas originais).
"""
import sys, os, glob, re, subprocess, functools

print = functools.partial(print, flush=True)  # senao intercala com o stdout dos subprocessos

SEC = 2048
AQUI = os.path.dirname(os.path.abspath(__file__))
ISO_ORIGINAL = os.path.join(AQUI, '..', '..',
                             'Tales_of_the_World_Radiant_Mythology_3_JPN_PSP-Caravan.iso')
CATALOGO = os.path.join(AQUI, '..', 'dados', 'bdi_catalogo2.csv')
DIR_LOTES = os.path.join(AQUI, '..', 'lotes')
DIR_EBOOT = os.path.join(AQUI, '..', 'eboot')
LBA_BDI = 106896
LBA_EBOOT = 560
TAM_EBOOT = 5863040  # EBOOT_dec_LIMPO.bin e todo build enNN: mesmo tamanho (P-44)


def eboot_mais_recente():
    """Maior NN em EBOOT_dec_enNN.bin dentro de DIR_EBOOT. Nunca o LIMPO."""
    candidatos = []
    for p in glob.glob(os.path.join(DIR_EBOOT, 'EBOOT_dec_en*.bin')):
        m = re.search(r'EBOOT_dec_en(\d+)\.bin$', os.path.basename(p))
        if m:
            candidatos.append((int(m.group(1)), p))
    if not candidatos:
        return None
    return max(candidatos)[1]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    iso_out = sys.argv[1]
    aplicar = '--aplicar' in sys.argv
    forcar = '--forcar' in sys.argv
    eboot = None
    if '--eboot' in sys.argv:
        eboot = sys.argv[sys.argv.index('--eboot') + 1]

    if not eboot:
        eboot = eboot_mais_recente()
    if not eboot:
        print('RECUSADO: nenhum EBOOT_dec_enNN.bin encontrado em', DIR_EBOOT)
        return 1

    print(f'ISO original : {ISO_ORIGINAL}')
    print(f'dialogo      : {DIR_LOTES}')
    print(f'EBOOT        : {eboot}  <- {"escolhido" if "--eboot" in sys.argv else "mais recente detectado"}')
    print(f'saida        : {iso_out}')
    print(f'modo         : {"APLICAR" if aplicar else "dry-run"}')
    print()

    # 1) dialogo — sempre a partir da ISO ORIGINAL, nunca de um build anterior
    cmd1 = [sys.executable, os.path.join(AQUI, 'bdi_build_iso.py'),
            ISO_ORIGINAL, str(LBA_BDI), CATALOGO, DIR_LOTES, iso_out]
    if aplicar:
        cmd1.append('--aplicar')
    if forcar:
        cmd1.append('--forcar')
    print('== ETAPA 1/2 — dialogo ==')
    r1 = subprocess.run(cmd1)
    if r1.returncode != 0:
        print('RECUSADO: etapa de dialogo falhou, EBOOT nao foi tocado.')
        return r1.returncode

    if not aplicar:
        print('\n== ETAPA 2/2 — EBOOT (nao roda em dry-run da etapa 1; '
              'rode com --aplicar para ver as duas) ==')
        return 0

    # 2) EBOOT — sobre a MESMA saida, regiao disjunta da do bdi (P-53)
    cmd2 = [sys.executable, os.path.join(AQUI, 'iso_troca_eboot.py'),
            iso_out, str(LBA_EBOOT), str(TAM_EBOOT), eboot, '--aplicar']
    print('\n== ETAPA 2/2 — EBOOT ==')
    r2 = subprocess.run(cmd2)
    if r2.returncode != 0:
        print('RECUSADO: EBOOT nao foi aplicado. A ISO tem dialogo mas ficou '
              'com o EBOOT ERRADO — nao distribua nem teste esta saida assim.')
        return r2.returncode

    print(f'\nOK — {iso_out} tem as duas frentes: dialogo (RM3/lotes/) + '
          f'EBOOT ({os.path.basename(eboot)}).')
    return 0


if __name__ == '__main__':
    sys.exit(main())

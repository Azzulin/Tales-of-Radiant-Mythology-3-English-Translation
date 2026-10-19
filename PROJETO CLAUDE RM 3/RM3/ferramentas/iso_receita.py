#!/usr/bin/env python3
"""A receita INTEIRA de uma ISO de teste, da original ate' a final, num comando.

Existia so' escrita no ESTADO_DO_PROJETO.md, e cada ISO nova dependia de alguem
lembrar os 11 passos na ordem (P-53, P-62.2, P-73: toda vez que um passo foi
esquecido, uma frente ja' traduzida voltou ao japones sem aviso). O
`iso_build_teste.py` conhece so' 2 deles.

Antes do passo 0, `bdi_orcamento_span.py` mede quanto cada entrada de dialogo
precisa com os lotes atuais. Passo 0 e' o `bdi_cresce.py --sob-medida` (P-84.2):
so' as entradas que nao cabem crescem, e o que elas precisam. Todo o resto sai
com o tamanho original, porque crescer entrada que nao precisa travou a Sinopse
na `en21`. Os passos seguintes sao as
ferramentas de sempre, sem mudanca, cada uma sobre a saida da anterior.

Cada passo escreve numa ISO intermediaria nova; a anterior e' apagada assim que
a seguinte existe (use --manter para guardar todas). Qualquer passo que falhe
para a receita inteira. O log completo fica em <saida>.log.

Um passo que PULE cena ou string por falta de espaco e' falha, nao aviso: com
o crescimento sob medida isso nao deveria acontecer, e se acontecer a ISO sairia
com japones onde ha' traducao.

Depois do ultimo passo roda, somente leitura, `frentes_bytes_controle.py`
original x final (P-82).

Uso:
  iso_receita.py <iso_original> <iso_saida> [--eboot eboot/EBOOT_dec_en23.bin]
                 [--margem N] [--manter] [--aplicar]
"""
import sys, os, re, subprocess, argparse, time, shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)            # RM3/: os caminhos da receita sao relativos a ela
LBA = '106896'
CAT = 'dados/bdi_catalogo2.csv'
NO_LUGAR = ('iso_eboot_realoca.py', 'eboot_oldata_tabela.py', 'eboot_local.py')   # escrevem na propria ISO
# lotes cena/ordem, aplicados por bdi_cenas_build_iso.py; a medicao de espaco os soma
LOTES_CENA = ['lotes/CAMPO-01_retorno.tsv', 'lotes_p68/CAMPO-02_retorno.tsv',
              'lotes_p68/CAMPO-03_retorno.tsv']


def passos(margem, eboot, orcamento, orcamento_cenas):
    """(rotulo, ferramenta, argumentos) — ENTRADA e SAIDA sao preenchidos em ordem."""
    E, S = '{ENTRADA}', '{SAIDA}'
    return [
        ('cresce o namco.bdi sob medida (P-84.2)', 'bdi_cresce.py',
         [E, S, '--sob-medida', orcamento, orcamento_cenas, '--margem', str(margem)]),
        ('dialogo .scr (todas as frentes FaceChat)', 'bdi_build_iso.py', [E, LBA, CAT, 'lotes', S]),
        ('quadro de quest .txz (P-82)', 'txz_build_iso.py', [E, LBA, CAT, 'lotes', S]),
        ('nomes completos CName (v3082)', 'ptrtab_build_iso.py', [E, '3082', 'dados/ficha_nomes.csv', S]),
        ('cenas avulsas CAMPO-01', 'bdi_cenas_build_iso.py', [E, S, CAT, 'lotes/CAMPO-01_retorno.tsv']),
        ('opcoes de campo CAMPO-02 (P-81.B)', 'bdi_cenas_build_iso.py', [E, S, CAT, 'lotes_p68/CAMPO-02_retorno.tsv']),
        ('rotulos e opcoes CAMPO-03 (P-88)', 'bdi_cenas_build_iso.py', [E, S, CAT, 'lotes_p68/CAMPO-03_retorno.tsv']),
        ('titulos de skit v2063', 'bdi_banco_build_iso.py', [E, S, 'campofixo', '2063', 'lotes_bancos/SKITBDI-*_retorno.tsv']),
        ('sinopse v2069 (P-71, P-83)', 'bdi_banco_build_iso.py', [E, S, 'oldata', '2069', 'dados/sinopse_com_cor.tsv']),
        ('capitulos v2070, a tela de Sinopse (P-86)', 'bdi_banco_build_iso.py',
         [E, S, 'oldata', '2070', 'lotes_bancos/CAPITULO-*_retorno.tsv', '--largura-dupla', '26']),
        ('perfis ORG (v3082)', 'bdi_banco_build_iso.py', [E, S, 'ptrtab', '3082', 'lotes_bancos/PERFIL-ORG_retorno.tsv', '--arquivo', 'CharGuideTextORG.bin']),
        ('perfis TOW3 (v3082)', 'bdi_banco_build_iso.py', [E, S, 'ptrtab', '3082', 'lotes_bancos/PERFIL-TOW3_retorno.tsv', '--arquivo', 'CharGuideTextTOW3.bin']),
        ('guia do jogo v2065 (P-89)', 'bdi_banco_build_iso.py', [E, S, 'guia', '2065', 'lotes_bancos/GUIA-01_retorno.tsv']),
        ('encantacao do Judas .zqe (v3330)', 'bdi_inplace_build_iso.py', [E, S, '3330', 'cJudas_Majinrengokusatsu_0.zqe', 'lotes_bancos/ZQE-JUDAS_retorno.tsv']),
        ('fecha o namco.bdi: tamanho exato e campo A (P-87)', 'bdi_fecha.py', ['{ORIGINAL}', E, S]),
        # o EBOOT com segmento de transbordo e' maior que o original: vai para um
        # buraco zerado da ISO e o registro de diretorio e' reescrito (P-91)
        ('EBOOT traduzido (P-91)', 'iso_eboot_realoca.py', [S, eboot]),
        ('tabela da Sinopse no EBOOT (P-86)', 'eboot_oldata_tabela.py', [S]),
        ('strings avulsas do EBOOT (P-88)', 'eboot_local.py', [S, 'dados/eboot_local.tsv']),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_original')
    ap.add_argument('iso_saida')
    ap.add_argument('--eboot', default='eboot/EBOOT_dec_en23.bin')
    ap.add_argument('--margem', type=int, default=0)
    ap.add_argument('--manter', action='store_true')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()

    orig = os.path.abspath(a.iso_original)
    saida = os.path.abspath(a.iso_saida)
    if orig == saida or 'Caravan.iso' in os.path.basename(saida):
        print('RECUSADO: a saida nao pode ser a ISO original')
        return 1
    if os.path.exists(saida):
        print('RECUSADO: %s ja existe' % saida)
        return 1
    eboot = os.path.join(RAIZ, a.eboot)
    if not os.path.exists(eboot):
        print('RECUSADO: EBOOT %s nao existe' % eboot)
        return 1
    etapas = saida + '.etapas'
    orcamento = os.path.join(etapas, 'orcamento_span.csv')
    orcamento_cenas = os.path.join(etapas, 'orcamento_span_com_cenas.csv')
    lista = passos(a.margem, eboot, orcamento, orcamento_cenas)

    print('receita: %d passos, de %s para %s\n' % (len(lista), orig, saida))
    for i, (rot, ferr, args) in enumerate(lista):
        print('  %2d  %-44s %s' % (i, rot, ferr))
    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0

    os.makedirs(etapas, exist_ok=False)
    log = open(saida + '.log', 'w', encoding='utf-8')
    # dois estados: so' o dialogo (fim do passo 1) e dialogo + CAMPO (fim dos
    # passos de cena). Um lote CAMPO pode ENCOLHER a cena, entao o estado do meio
    # pode precisar de mais espaco que o final (P-88, cev47_060)
    print('[--] mede o orcamento de cada entrada ...', end=' ', flush=True)
    for csv_saida, extra in ((orcamento, []), (orcamento_cenas, ['--cenas'] + LOTES_CENA)):
        r = subprocess.run([sys.executable, os.path.join(AQUI, 'bdi_orcamento_span.py'), orig, LBA,
                            CAT, 'lotes', '--csv', csv_saida] + extra,
                           cwd=RAIZ, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        log.write('===== orcamento %s\n' % csv_saida + r.stdout.decode('utf-8', 'replace'))
        if r.returncode != 0 or not os.path.exists(csv_saida):
            print('FALHOU')
            return 1
    print('ok')

    # bancos: dry-run de cada um contra a original; o que faltar vira folga
    # sob medida para aquela entrada no passo 0 (o byte nao e' limite, P-84.2)
    extras = []
    for rot, ferr, args in lista:
        if ferr != 'bdi_banco_build_iso.py':
            continue
        cmd = [sys.executable, os.path.join(AQUI, ferr)] +               [x.replace('{ENTRADA}', orig).replace('{SAIDA}', saida + '.medida') for x in args]
        r = subprocess.run(cmd, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        t = r.stdout.decode('utf-8', 'replace')
        m = re.search(r'(?:faltam|estoura o span em) (\d+)', t)
        if m:
            n = -(-int(m.group(1)) // 2048)
            extras += ['--entrada', '%s:+%d' % (args[3], n)]
            print('[--] %s precisa de +%d setor(es)' % (rot, n))
    lista[0] = (lista[0][0], lista[0][1], lista[0][2] + extras)
    entrada, anterior = orig, None
    t0 = time.time()
    for i, (rot, ferr, args) in enumerate(lista):
        no_lugar = ferr in NO_LUGAR
        if no_lugar:
            # troca de EBOOT e tabela da Sinopse escrevem in-place sobre a copia:
            # a intermediaria vira a final
            if entrada != saida:
                shutil.move(entrada, saida)
            anterior = None
            s = saida
        else:
            s = os.path.join(etapas, '%02d.iso' % i)
        cmd = [sys.executable, os.path.join(AQUI, ferr)] + \
              [x.replace('{ENTRADA}', entrada).replace('{SAIDA}', s).replace('{ORIGINAL}', orig)
               for x in args] + ['--aplicar']
        print('[%2d] %s ...' % (i, rot), end=' ', flush=True)
        log.write('\n===== [%d] %s\n$ %s\n' % (i, rot, ' '.join(cmd)))
        log.flush()
        r = subprocess.run(cmd, cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        texto = r.stdout.decode('utf-8', 'replace')
        log.write(texto)
        log.flush()
        if r.returncode != 0 or not os.path.exists(s):
            print('FALHOU (codigo %d)' % r.returncode)
            print('\n'.join('     ' + l for l in texto.strip().splitlines()[-15:]))
            print('\nreceita interrompida. Log: %s' % (saida + '.log'))
            return 1
        pulou = [int(m) for m in re.findall(r'(\d+) (?:cenas puladas|pulados)', texto, re.I)]
        if any(pulou):
            print('FALHOU: o passo pulou %d item(ns) por falta de espaco' % sum(pulou))
            print('suba a folga dessa entrada com --margem, ou veja o log: %s' % (saida + '.log'))
            return 1
        print('ok (%.0f s)' % (time.time() - t0))
        for l in texto.splitlines():
            if any(k in l.lower() for k in ('pulad', 'nao cab', 'recusad', 'aviso')):
                print('       ' + l.strip())
        if anterior and anterior != orig and not a.manter:
            os.remove(anterior)
        anterior, entrada = s, s
    if not a.manter:
        shutil.rmtree(etapas, ignore_errors=True)

    print('\nconferencia de bytes de controle (original x final):')
    r = subprocess.run([sys.executable, os.path.join(AQUI, 'frentes_bytes_controle.py'), orig, saida],
                       cwd=RAIZ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    texto = r.stdout.decode('utf-8', 'replace')
    log.write('\n===== frentes_bytes_controle\n' + texto)
    print(texto)
    print('pronto em %.0f s: %s (%d B)' % (time.time() - t0, saida, os.path.getsize(saida)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

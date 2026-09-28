#!/usr/bin/env python3
"""Teste de reinsercao sintetica: troca titulo/corpo por texto de tamanho
DIFERENTE do original, reconstroi e reanalisa com parse(strict=True) para
provar que o build() recalcula offsets e nao corrompe a arvore quando o
tamanho do texto muda -- e' exatamente o bloqueio que o P-28 original
apontava (offsets absolutos = qualquer mudanca de tamanho desloca o pool).

NAO prova que o jogo aceita -- so que o parser/builder sao mecanicamente
consistentes com tamanho variavel. Ver relatorio.md.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guia2

NUL = b'\x00'


def carrega(iso, lba, size, ferramentas_dir, v=2065):
    sys.path.insert(0, ferramentas_dir)
    import bdi
    with open(iso, 'rb') as f:
        base = lba * 2048
        buckets, count, entries, sent = bdi.load_index(f, base)
        bad = bdi.validate(buckets, count, entries, sent, size)
        if bad:
            raise SystemExit('indice bdi reprovou: %s' % bad)
        e = [x for x in entries if x['v'] == v][0]
        f.seek(base + e['off'])
        return f.read(e['span']), e


def main():
    iso, lba, size, ferramentas_dir = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    data, e = carrega(iso, lba, size, ferramentas_dir)
    p = guia2.parse(data, strict=True)
    orig_bytes = len(data)
    print('span reservado=%d  conteudo original=%d  folga=%d'
          % (e['span'], guia2.tamanho_projetado(p), e['span'] - guia2.tamanho_projetado(p)))

    # --- caso 1: texto MAIOR que o original, dentro da folga ---
    alvo = 5
    original_titulo = guia2.decode(p['regs'][alvo]['titulo'])
    original_corpo = guia2.decode(p['regs'][alvo]['corpo'])
    print('registro %d ANTES: titulo=%r corpo_len=%d' % (alvo, original_titulo, len(p['regs'][alvo]['corpo'])))
    novo_titulo = 'MENU DE TESTE MAIOR QUE O ORIGINAL'
    novo_corpo = ('Traducao de teste, deliberadamente mais longa que o texto '
                  'japones original, para provar que o build() recalcula os '
                  'offsets absolutos de todos os registros seguintes sem '
                  'corromper a arvore pai/filho nem o pool de ordem.\n'
                  'Segunda linha.\nTerceira linha.')
    p['regs'][alvo]['titulo'] = guia2.encode(novo_titulo)
    p['regs'][alvo]['corpo'] = guia2.encode(novo_corpo)
    guia2.recalcular_B(p)
    novo = guia2.build_para_span(p, e['span'])
    print('build_para_span OK: %d bytes (span=%d)' % (len(novo), e['span']))

    p2 = guia2.parse(novo, strict=True)
    print('reparse do arquivo modificado: strict OK, avisos=%s' % p2['avisos'])
    print('registro %d DEPOIS: titulo=%r corpo=%r B=%d' % (
        alvo, guia2.decode(p2['regs'][alvo]['titulo']), guia2.decode(p2['regs'][alvo]['corpo'])[:40], p2['regs'][alvo]['B']))
    assert p2['regs'][alvo]['titulo'] == guia2.encode(novo_titulo)
    assert p2['regs'][alvo]['corpo'] == guia2.encode(novo_corpo)
    assert p2['regs'][alvo]['B'] == novo_corpo.count('\n') + 1

    # confirma que TODOS os outros registros continuam intactos (texto, arvore, A/C/D)
    intactos = 0
    for i in range(p['count']):
        if i == alvo:
            continue
        r1, r2 = p['regs'][i], p2['regs'][i]
        ok = (r1['id'] == r2['id'] and r1['parent'] == r2['parent'] and
              r1['A'] == r2['A'] and r1['C'] == r2['C'] and r1['D'] == r2['D'] and
              r1['filho_ini'] == r2['filho_ini'] and r1['filho_num'] == r2['filho_num'] and
              r1['titulo'] == r2['titulo'] and r1['corpo'] == r2['corpo'])
        intactos += ok
    print('registros nao mexidos continuam byte-identicos (texto+A+C+D+arvore): %d/%d'
          % (intactos, p['count'] - 1))
    print('arvore ainda valida (parse com strict=True nao levantou) -> pool de ordem e faixas OK')

    # --- caso 2: estourar a folga do span reservado -> build_para_span deve RECUSAR ---
    p3 = guia2.parse(data, strict=True)
    folga = e['span'] - guia2.tamanho_projetado(p3)
    texto_grande = 'X' * (folga + 500)
    p3['regs'][alvo]['corpo'] = guia2.encode(texto_grande)
    guia2.recalcular_B(p3)
    try:
        guia2.build_para_span(p3, e['span'])
        print('FALHOU: build_para_span deveria ter recusado (excedeu span)')
    except ValueError as ex:
        print('build_para_span recusou corretamente o excesso de span:', str(ex)[:90])

    # --- caso 3: esquecer recalcular_B -> build() deve recusar ---
    p4 = guia2.parse(data, strict=True)
    p4['regs'][alvo]['corpo'] = guia2.encode('outra frase\ncom mais linhas\nque o original\ntinha')
    try:
        guia2.build(p4)
        print('FALHOU: build() deveria ter recusado B desatualizado')
    except ValueError as ex:
        print('build() recusou corretamente B desatualizado:', str(ex)[:90])


main()

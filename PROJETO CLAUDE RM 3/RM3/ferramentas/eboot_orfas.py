#!/usr/bin/env python3
"""As strings orfas do EBOOT: japones com ponteiro, fora de todo lote (P-92).

`eboot_auditoria_codigo.py` achou 828 strings japonesas que um u32 do binario
aponta e que nenhum lote do build cobre: dialogos de confirmacao, efeitos de
culinaria, falas de companheiro em quest, anuncios do Colosseum, faixas do
jukebox... O inventario do P-54/P-68 partiu de tabelas de ponteiro grandes e
deixou de fora o ponteiro que mora sozinho num registro.

Estrategia de build, a mais conservadora que existe:
  - cada string e' o seu proprio bloco (`orfa__<va>`), com arena = o SLOT dela:
    do inicio ate' o proximo byte nao zero depois do terminador (o padding
    de alinhamento conta como espaco da propria string);
  - se o ingles cabe no slot, ele fica NO MESMO ENDERECO: nada se move;
  - se nao cabe, vai para o segmento de transbordo (`eboot_build2.py
    --transborda`) e, com a coluna `preserva=1`, o slot fica com os bytes
    originais intactos (quem ler a regiao por calculo, P-70, le o japones de
    antes, nao zeros).

Modos:
  extrai <auditoria.csv> <eboot_limpo> <lote.tsv> <ponteiros.csv>
      gera o lote de traducao (uma linha por texto distinto, como os SIS-NN)
      e o CSV de ponteiros (uma linha por ponteiro, sem traducao)
  monta <ponteiros.csv> <retorno.tsv> <saida.csv>
      junta as traducoes num CSV que o `eboot_build2.py` consome; texto sem
      traducao vira `(verbatim)`

So' le o EBOOT; nunca escreve nele.
"""
import sys, re, csv, struct, collections

DELTA = 0x08803000
ELF_FIM = 5862704
COLS_BUILD = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'id', 'original',
              'arena_ini', 'arena_fim', 'preserva']


def extrai(aud, eboot, lote, ponteiros):
    d = open(eboot, 'rb').read()[:ELF_FIM]
    rs = [r for r in csv.DictReader(open(aud, encoding='utf-8')) if r['classe'] == 'ptr_fora_de_lote']
    alvo = {int(r['va'], 16): r for r in rs}
    onde = collections.defaultdict(list)
    for q in range(0x1000, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, q)[0]
        if v in alvo:
            onde[v].append(q + DELTA)
    # todo endereco que algum u32 ou par lui/lo do codigo usa: o slot de uma
    # string nao pode engolir nenhum deles (um NUL de padding pode ser o "texto
    # vazio" de outro ponteiro, P-77/p68_vazias)
    import prx, eboot_auditoria_codigo
    usados = set(struct.unpack_from('<I', d, q)[0] for q in range(0x1000, len(d) - 3, 4))
    sec = {x['name']: x for x in prx.ler(d)['secs']}
    t = sec['.text']
    usados |= set(eboot_auditoria_codigo.pares_codigo(d, t['off'], t['off'] + t['size']))
    linhas, por_texto = [], collections.OrderedDict()
    for va in sorted(alvo):
        r = alvo[va]
        p = va - DELTA
        n = int(r['bytes'])
        assert d[p + n] == 0
        fim = p + n + 1
        while fim < len(d) and d[fim] == 0 and (fim - p) < 4096 and (fim + DELTA) not in usados:
            fim += 1
        # o dado seguinte pode comecar com byte zero (u32 0x08D14800 = 00 48 D1 08):
        # o slot termina no ultimo multiplo de 4, nunca menos que a propria string
        fim = max(p + n + 1, (fim + DELTA) // 4 * 4 - DELTA)
        texto = d[p:p + n].decode('euc_jp')
        tid = por_texto.setdefault(texto, {'id': 'SIS05-%04d' % (len(por_texto) + 1), 'vas': [], 'slot': fim - p})
        tid['vas'].append(va)
        tid['slot'] = min(tid['slot'], fim - p)
        for vp in onde[va]:
            linhas.append({'bloco': 'orfa__%08X' % va, 'va_ponteiro': '0x%08X' % vp,
                           'va_string': '0x%08X' % va, 'bytes_jp': n, 'traducao': '',
                           'id': tid['id'], 'original': texto.replace('\n', '\\n'),
                           'arena_ini': '0x%08X' % va, 'arena_fim': '0x%08X' % (fim + DELTA),
                           'preserva': '1'})
    with open(ponteiros, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS_BUILD)
        w.writeheader()
        w.writerows(linhas)
    with open(lote, 'w', encoding='utf-8', newline='') as f:
        f.write('id\tva_strings\tbytes_slot\toriginal\ttraducao\n')
        for t, x in por_texto.items():
            f.write('%s\t%s\t%d\t%s\t\n' % (x['id'], ';'.join('0x%08X' % v for v in x['vas']), x['slot'],
                                            t.replace('\t', '\\t').replace('\n', '\\n')))
    print('%d strings, %d textos distintos, %d ponteiros -> %s, %s'
          % (len(alvo), len(por_texto), len(linhas), lote, ponteiros))
    sem = [v for v in alvo if not onde[v]]
    if sem:
        print('AVISO: %d strings sem ponteiro achado na releitura' % len(sem))
    return 0


def monta(ponteiros, retorno, saida):
    tr = {}
    for r in csv.DictReader(open(retorno, encoding='utf-8'), delimiter='\t'):
        t = (r.get('traducao') or '').strip()
        if t:
            tr[r['id']] = t
    rs = list(csv.DictReader(open(ponteiros, encoding='utf-8')))
    ruins, avisos, saem, fora = [], [], [], 0
    vistos = {}
    for r in rs:
        t = tr.get(r['id'])
        if t is None or t == '(verbatim)':
            # sem traducao: a string NAO entra no lote e fica onde esta, sem
            # arena nenhuma (a guarda 2d recusaria arena sobre string que o
            # codigo enderecar direto, e nao ha' o que reempacotar)
            fora += 1
            continue
        if r['id'] not in vistos:
            vistos[r['id']] = confere_linha(r['original'], t)
            if vistos[r['id']][0]:
                ruins.append((r['id'], vistos[r['id']][0]))
            avisos += [(r['id'], x) for x in vistos[r['id']][1]]
        # o `eboot_build2.py` so' converte o token \n; o TAB de controle (SIS05-0173
        # comeca com um) vai para o CSV ja' como o byte 0x09
        r['traducao'] = t.replace(chr(92) + 't', chr(9))
        saem.append(r)
    for i, x in avisos[:40]:
        print('  aviso %s: %s' % (i, x))
    if ruins:
        print('RECUSADO: %d textos com problema:' % len(ruins))
        for i, x in ruins[:30]:
            print('  %s: %s' % (i, x))
        return 1
    with open(saida, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=COLS_BUILD)
        w.writeheader()
        w.writerows(saem)
    print('%d ponteiros: %d com traducao (%d textos), %d sem traducao ficam fora do lote; '
          '%d avisos -> %s' % (len(rs), len(saem), len(vistos), fora, len(avisos), saida))
    return 0


TOKENS = ('＜数＞', '＜残＞', '＜ダンジョン名＞', '＜モンスター名＞', '○○')
SIMBOLOS = set('○×△□■→★％')
FMT = re.compile(r'%[-+ 0#]*\d*(?:\.\d+)?[sdfcxuX]')
LARGURA = 40


def confere_linha(orig, tr):
    """(erro ou '', [avisos]) — as regras duras do briefing do SIS-05."""
    o = orig.replace('\\n', '\n')
    t = tr.replace('\\n', '\n')
    for k in TOKENS:
        if o.count(k) != t.count(k):
            return 'token %s: %d no original, %d na traducao' % (k, o.count(k), t.count(k)), []
    resto = t
    for k in TOKENS:
        resto = resto.replace(k, '')
    ruim = sorted({c for c in resto if not (c.isascii() or c in SIMBOLOS)})
    if ruim:
        return 'caractere fora do permitido: %s' % ''.join(ruim), []
    if any(ord(c) < 32 and c != '\n' for c in resto):
        return 'caractere de controle', []
    if FMT.findall(o) != FMT.findall(t):
        return 'printf %s -> %s' % (FMT.findall(o), FMT.findall(t)), []
    if '%' in FMT.sub('', t):
        return '%% ASCII que nao e especificador', []
    if o.count('#') != t.count('#'):
        return '# %d -> %d' % (o.count('#'), t.count('#')), []
    if o.count('\n') != t.count('\n'):
        return 'linhas %d -> %d' % (o.count('\n') + 1, t.count('\n') + 1), []
    av = []
    for ln in re.split('[\n#]', t):
        if len(ln) > LARGURA:
            av.append('linha de %d caracteres: %r' % (len(ln), ln[:30]))
    return '', av


def main():
    if len(sys.argv) >= 6 and sys.argv[1] == 'extrai':
        return extrai(*sys.argv[2:6])
    if len(sys.argv) >= 5 and sys.argv[1] == 'monta':
        return monta(*sys.argv[2:5])
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())

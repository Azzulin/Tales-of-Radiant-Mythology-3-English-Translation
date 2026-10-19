#!/usr/bin/env python3
"""Gera uma ISO com o `namco.bdi` MAIOR: cada entrada que nao cabe ganha os setores
que precisa, e o byte deixa de ser limite para a traducao (P-84, P-84.2).

E' o passo 0 da receita de build. Roda sobre a ISO original e devolve uma ISO
com o mesmo conteudo, so' que com espaco sobrando dentro de cada entrada. Todas
as ferramentas seguintes (`bdi_build_iso.py`, `txz_build_iso.py`, ...) leem o
span de cada entrada do proprio indice, entao passam a ver a folga sem mudar
uma linha.

Por que o `namco.bdi` inteiro e' reescrito (P-14/P-84):
  o indice nao guarda tamanho. `nsect = setor(v+1) - setor(v)`, e as entradas
  ficam em ordem de setor. Crescer uma entrada exige DESLOCAR todas as seguintes.
  Em cada registro so' os bits de setor (30..11) mudam; flag (31), campo A
  (10..0, nao decifrado) e chave sao preservados, e a tabela hash nao muda
  porque a ordem nao muda. A sentinela vira o novo tamanho / 2048.

Por que isso funciona no jogo (P-84):
  o EBOOT nao tem LBA nem tamanho do `namco.bdi` gravados. Ele lista
  `disc0:/PSP_GAME/USRDIR`, le tamanho e LBA da entrada de diretorio e monta
  `disc0:/sce_lbn0x%x_size0x%x`. Basta o registro de diretorio estar certo.

Na ISO:
  o `namco.bdi` so' tem 2 setores livres depois dele. Os arquivos seguintes
  (`INSDIR/ICON0.PNG`, `NAMCO.MDI`, `PIC1.PNG`) sao deslocados D setores para
  frente, D = crescimento arredondado a 16 (o alinhamento que eles ja tem).
  Atualiza o extent deles, o tamanho do `namco.bdi` e o volume space do PVD.

Seguranca:
  - so' abre a ISO de entrada em 'rb'; recusa saida == entrada ou saida com
    cara de ISO original; dry-run sem `--aplicar`;
  - depois de escrever, RELE a ISO gerada e confere: arvore ISO9660, indice
    (`bdi.validate`), cada entrada byte a byte contra a original, folga zerada,
    arquivos deslocados identicos, e todo o resto da ISO identico fora dos
    setores que deveriam mudar.

SO' CRESCE O QUE PRECISA (P-84.2). A primeira versao dava +1 setor a todas as
2.232 entradas com texto, e a `en21` travou ao abrir a Sinopse: o `v2069` ocupava
o span inteiro (45.056 B) e passou a 47.104 B. O jogo le a entrada pelo span, e
2 KB a mais transbordam o buffer. Uma entrada que nao precisa crescer tem de
sair com o tamanho ORIGINAL.

Uso:
  bdi_cresce.py <iso_in> <iso_out> [--sob-medida orcamento.csv] [--margem N]
                [--entrada V:+N ...] [--extra N] [--aplicar]

  --sob-medida CSV  o CSV do `bdi_orcamento_span.py --csv`: cada entrada com
                    folga negativa ganha os setores que faltam (+ --margem)
  --entrada V:+N    setores a mais para a entrada V; repetivel
  --extra N         setores para TODA entrada com texto (padrao 0; nao use sem
                    saber o que o jogo faz com o span de cada uma, ver P-84.2)
"""
import sys, os, csv, struct, argparse, hashlib, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bdi import load_index, validate, REC_BASE

SEC = 2048
LBA_BDI = 106896
ALINHA = 16                     # alinhamento dos arquivos do INSDIR, em setores
NOME_BDI = 'NAMCO.BDI'
BANCOS = {2063, 2065, 2069, 2070, 3082, 3330}   # P-26..P-29, P-57, P-69, P-73
EXT_TEXTO = ('.scr', '.txz', '.zqe')
BLOCO = 8 * 2 ** 20
ZERO_SEC = b'\x00' * SEC
MASCARA_SETOR = 0xFFFFF << 11


# ---------- ISO9660 com posicao de cada registro ----------

def registros(f, lba, tam, prefixo=''):
    """Percorre a arvore devolvendo (caminho, eh_dir, lba, tam, pos_do_registro)."""
    f.seek(lba * SEC)
    dado = f.read(tam)
    i = 0
    while i < len(dado):
        rl = dado[i]
        if rl == 0:
            i = (i // SEC + 1) * SEC
            continue
        r = dado[i:i + rl]
        ext = struct.unpack_from('<I', r, 2)[0]
        sz = struct.unpack_from('<I', r, 10)[0]
        eh_dir = bool(r[25] & 2)
        nome = r[33:33 + r[32]]
        pos = lba * SEC + i
        i += rl
        if nome in (b'\x00', b'\x01'):
            continue
        caminho = prefixo + '/' + nome.decode('latin1').split(';')[0]
        yield caminho, eh_dir, ext, sz, pos
        if eh_dir:
            yield from registros(f, ext, sz, caminho)


def arvore(f):
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    if pvd[1:6] != b'CD001' or pvd[0] != 1:
        raise ValueError('PVD invalido')
    f.seek(17 * SEC)
    if f.read(1)[0] != 255:
        raise ValueError('ha um segundo descritor de volume (Joliet?) — nao suportado')
    root = pvd[156:190]
    rl, rs = struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]
    vss = struct.unpack_from('<I', pvd, 80)[0]
    return list(registros(f, rl, rs)), vss


def pack_ambos(v):
    return struct.pack('<I', v) + struct.pack('>I', v)


# ---------- plano ----------

def entradas_com_texto(catalogo):
    vs = set(BANCOS)
    with open(catalogo, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['nome'].lower().endswith(EXT_TEXTO):
                vs.add(int(r['entrada_v']))
    return vs


def planeja(f, extra, extras_v, com_texto, ajuste=None):
    """`ajuste` = {v: (nsect_novo, A_novo)} (usado pelo `bdi_fecha.py`, P-87): fixa o
    tamanho e o campo A de cada entrada, podendo tambem ENCOLHER."""
    arv, vss = arvore(f)
    bdi = [x for x in arv if not x[1] and x[0].upper().endswith('/' + NOME_BDI)]
    if len(bdi) != 1:
        raise ValueError('namco.bdi nao encontrado (ou duplicado) na ISO')
    _, _, lba, tam_bdi, pos_bdi = bdi[0]
    if lba != LBA_BDI:
        raise ValueError('namco.bdi no LBA %d, esperado %d' % (lba, LBA_BDI))
    base = lba * SEC
    buckets, count, ents, sentinela = load_index(f, base)
    falhas = validate(buckets, count, ents, sentinela, tam_bdi)
    if falhas:
        raise ValueError('indice do namco.bdi da entrada nao valida: %s' % falhas)
    fim_bdi = lba + tam_bdi // SEC
    depois = [x for x in arv if x[2] >= fim_bdi and x[3] > 0]
    if any(x[1] for x in depois):
        raise ValueError('ha diretorio depois do namco.bdi — nao suportado')

    add = {}
    for e in ents:
        n = (extra if e['v'] in com_texto else 0) + extras_v.get(e['v'], 0)
        if n:
            add[e['v']] = n
    novo_A = {}
    for v, (ns, a_novo) in (ajuste or {}).items():
        e = {x['v']: x for x in ents}.get(v)
        if not e:
            raise ValueError('entrada %d inexistente no indice' % v)
        if not (0 <= a_novo < SEC) or ns < 1:
            raise ValueError('entrada %d: nsect %d / A %d invalidos' % (v, ns, a_novo))
        if ns != e['nsect']:
            add[v] = ns - e['nsect']
        else:
            add.pop(v, None)
        if a_novo != e['A']:
            novo_A[v] = a_novo
    desconhecidas = set(extras_v) - {e['v'] for e in ents}
    if desconhecidas:
        raise ValueError('entrada(s) inexistente(s) no indice: %s' % sorted(desconhecidas))
    g = sum(add.values())
    d = max(0, -(-g // ALINHA) * ALINHA)      # encolher nao puxa o INSDIR para tras

    novo_setor, acum = {}, 0
    for e in ents:
        novo_setor[e['v']] = e['sect'] + acum
        acum += add.get(e['v'], 0)
    sent_setor = sentinela // SEC + g
    if sent_setor >= 2 ** 20:
        raise ValueError('o namco.bdi passaria de 2 GB: o campo de setor tem 20 bits')
    return {
        'arv': arv, 'vss': vss, 'lba': lba, 'tam_bdi': tam_bdi, 'pos_bdi': pos_bdi,
        'fim_bdi': fim_bdi, 'depois': depois, 'ents': ents, 'count': count,
        'add': add, 'g': g, 'd': d, 'novo_setor': novo_setor, 'sent_setor': sent_setor,
        'tam_novo': sent_setor * SEC, 'buckets': buckets, 'novo_A': novo_A,
    }


def cabecalho_novo(f, pl):
    """Bytes do namco.bdi antes da 1a entrada, com os setores dos registros trocados."""
    ini = pl['ents'][0]['sect'] * SEC
    f.seek(pl['lba'] * SEC)
    cab = bytearray(f.read(ini))
    fim_regs = REC_BASE + (2 + pl['count'] + 1) * 8
    if fim_regs > ini:
        raise ValueError('o indice invade a area da 1a entrada')
    alvos = [(e['v'], pl['novo_setor'][e['v']]) for e in pl['ents']]
    alvos.append((2 + pl['count'], pl['sent_setor']))
    for v, s in alvos:
        p = REC_BASE + v * 8
        a = struct.unpack_from('<I', cab, p)[0]
        a = (a & ~MASCARA_SETOR & 0xFFFFFFFF) | (s << 11)
        if v in pl['novo_A']:                    # P-87: A = span - tamanho do arquivo
            a = (a & ~0x7FF) | pl['novo_A'][v]
        struct.pack_into('<I', cab, p, a)
    return bytes(cab)


# ---------- escrita ----------

def copia(fi, fo, ini, n):
    fi.seek(ini)
    while n > 0:
        b = fi.read(min(BLOCO, n))
        if not b:
            raise IOError('fim inesperado da ISO de entrada')
        fo.write(b)
        n -= len(b)


def escreve(iso_in, iso_out, pl):
    lba, d = pl['lba'], pl['d']
    with open(iso_in, 'rb') as fi, open(iso_out, 'xb') as fo:
        copia(fi, fo, 0, lba * SEC)
        fo.write(cabecalho_novo(fi, pl))
        for e in pl['ents']:
            n = pl['add'].get(e['v'], 0)
            copia(fi, fo, lba * SEC + e['off'], e['span'] + min(0, n) * SEC)
            fo.write(ZERO_SEC * max(0, n))
        # do fim antigo do namco.bdi ate' o fim da ISO, deslocado D setores
        fo.write(ZERO_SEC * (d - pl['g']))
        tam_iso = os.path.getsize(iso_in)
        copia(fi, fo, pl['fim_bdi'] * SEC, tam_iso - pl['fim_bdi'] * SEC)

        # registros de diretorio e PVD
        fo.seek(pl['pos_bdi'] + 10)
        fo.write(pack_ambos(pl['tam_novo']))
        for _, _, ext, _, pos in pl['depois']:
            fo.seek(pos + 2)
            fo.write(pack_ambos(ext + d))
        fo.seek(16 * SEC + 80)
        fo.write(pack_ambos(pl['vss'] + d))


# ---------- releitura ----------

def hash_trecho(f, ini, n):
    h = hashlib.sha1()
    f.seek(ini)
    while n > 0:
        b = f.read(min(BLOCO, n))
        h.update(b)
        n -= len(b)
    return h.hexdigest()


def confere(iso_in, iso_out, pl):
    lba, d, g = pl['lba'], pl['d'], pl['g']
    falhas = []
    with open(iso_in, 'rb') as fi, open(iso_out, 'rb') as fo:
        if os.path.getsize(iso_out) != os.path.getsize(iso_in) + d * SEC:
            falhas.append('tamanho da ISO gerada')
        arv_o, vss_o = arvore(fo)
        if vss_o != pl['vss'] + d:
            falhas.append('volume space size do PVD')
        velho = {x[0]: x for x in pl['arv']}
        for cam, eh_dir, ext, sz, _ in arv_o:
            v = velho.get(cam)
            if not v:
                falhas.append('arquivo novo na arvore: %s' % cam)
                continue
            esp_ext = v[2] + d if v[2] >= pl['fim_bdi'] and v[3] > 0 else v[2]
            esp_sz = pl['tam_novo'] if cam.upper().endswith('/' + NOME_BDI) else v[3]
            if ext != esp_ext or sz != esp_sz:
                falhas.append('%s: extent/tamanho %d/%d, esperado %d/%d'
                              % (cam, ext, sz, esp_ext, esp_sz))
        if len(arv_o) != len(pl['arv']):
            falhas.append('numero de registros na arvore mudou')

        buckets, count, ents, sent = load_index(fo, lba * SEC)
        f2 = validate(buckets, count, ents, sent, pl['tam_novo'])
        falhas += ['indice novo: ' + x for x in f2]
        if buckets != pl['buckets'] or count != pl['count']:
            falhas.append('tabela hash ou count mudou')
        for a, b in zip(pl['ents'], ents):
            a_esp = pl['novo_A'].get(a['v'], a['A'])
            if (a['v'], a['flag'], a_esp, a['key']) != (b['v'], b['flag'], b['A'], b['key']):
                falhas.append('registro v%d: flag/A/chave mudou' % a['v'])
                continue
            if b['sect'] != pl['novo_setor'][a['v']]:
                falhas.append('registro v%d: setor errado' % a['v'])
            fi.seek(lba * SEC + a['off'])
            orig = fi.read(a['span'])
            fo.seek(lba * SEC + b['off'])
            novo = fo.read(b['span'])
            m = min(len(orig), len(novo))
            if novo[:m] != orig[:m]:
                falhas.append('entrada v%d: conteudo difere' % a['v'])
            if novo[m:].strip(b'\x00'):
                falhas.append('entrada v%d: folga nao esta zerada' % a['v'])
            if orig[m:].strip(b'\x00'):
                falhas.append('entrada v%d: encolheu por cima de dado que nao era zero' % a['v'])
            if len(falhas) > 50:
                break

        # fora do namco.bdi: identico, exceto PVD e setores de diretorio
        mudam = {16} | {pl['pos_bdi'] // SEC} | {p // SEC for *_, p in pl['depois']}
        for s in range(0, lba):
            if s in mudam:
                continue
            fi.seek(s * SEC)
            fo.seek(s * SEC)
            if fi.read(SEC) != fo.read(SEC):
                falhas.append('setor %d antes do namco.bdi mudou' % s)
                break
        tam_iso = os.path.getsize(iso_in)
        n = tam_iso - pl['fim_bdi'] * SEC
        if hash_trecho(fi, pl['fim_bdi'] * SEC, n) != hash_trecho(fo, (pl['fim_bdi'] + d) * SEC, n):
            falhas.append('trecho depois do namco.bdi (INSDIR) difere')
    return falhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('iso_in')
    ap.add_argument('iso_out')
    ap.add_argument('--extra', type=int, default=0)
    ap.add_argument('--sob-medida', nargs='+', default=[])
    ap.add_argument('--margem', type=int, default=0)
    ap.add_argument('--entrada', action='append', default=[])
    ap.add_argument('--catalogo', default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'dados', 'bdi_catalogo2.csv'))
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()

    if os.path.abspath(a.iso_in) == os.path.abspath(a.iso_out):
        print('RECUSADO: entrada e saida sao a mesma ISO')
        return 1
    if 'Caravan.iso' in os.path.basename(a.iso_out):
        print('RECUSADO: a saida tem cara de ISO original')
        return 1
    if a.extra < 0:
        print('RECUSADO: --extra negativo')
        return 1
    extras_v = {}
    for t in a.entrada:
        v, _, n = t.partition(':+')
        if not n:
            print('RECUSADO: --entrada no formato V:+N (ex.: 6497:+2), recebido %r' % t)
            return 1
        extras_v[int(v)] = extras_v.get(int(v), 0) + int(n)

    # varios CSVs = varios ESTADOS intermediarios da receita (so' dialogo; dialogo
    # + CAMPO): a entrada precisa caber em todos, entao vale o MAIOR deles (P-88)
    sob = {}
    for caminho in a.sob_medida:
        with open(caminho, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                folga = int(r['folga'])
                if folga < 0:
                    n = -(-(-folga) // SEC) + a.margem
                    sob[int(r['v'])] = max(sob.get(int(r['v']), 0), n)
    for v, n in sob.items():
        extras_v[v] = extras_v.get(v, 0) + n
    com_texto = entradas_com_texto(a.catalogo)
    with open(a.iso_in, 'rb') as f:
        pl = planeja(f, a.extra, extras_v, com_texto)

    print('entradas no indice:        %d' % pl['count'])
    print('entradas que ganham folga: %d (%d com texto no catalogo)'
          % (len(pl['add']), len(com_texto)))
    print('crescimento do namco.bdi:  +%d setores (+%.1f MB): %d -> %d B'
          % (pl['g'], pl['g'] * SEC / 2 ** 20, pl['tam_bdi'], pl['tam_novo']))
    print('arquivos deslocados +%d setores:' % pl['d'])
    for cam, _, ext, sz, _ in pl['depois']:
        print('   %-32s LBA %d -> %d  (%d B)' % (cam, ext, ext + pl['d'], sz))
    print('ISO: %d -> %d setores' % (pl['vss'], pl['vss'] + pl['d']))

    if not a.aplicar:
        print('\nDRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    if os.path.exists(a.iso_out):
        print('RECUSADO: %s ja existe' % a.iso_out)
        return 1

    t0 = time.time()
    print('\nescrevendo %s ...' % a.iso_out, flush=True)
    escreve(a.iso_in, a.iso_out, pl)
    print('escrito em %.0f s. relendo e conferindo...' % (time.time() - t0), flush=True)
    falhas = confere(a.iso_in, a.iso_out, pl)
    if falhas:
        print('\nFALHOU A CONFERENCIA (%d). A ISO gerada NAO deve ser usada:' % len(falhas))
        for x in falhas[:30]:
            print('   ' + x)
        return 2
    print('conferencia OK em %.0f s: arvore, indice, %d entradas byte a byte, folga zerada, '
          'INSDIR e o resto da ISO identicos.' % (time.time() - t0, len(pl['ents'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())

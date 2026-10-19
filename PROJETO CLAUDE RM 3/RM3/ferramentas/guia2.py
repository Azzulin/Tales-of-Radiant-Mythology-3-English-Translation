#!/usr/bin/env python3
"""Formato GUIA (v2, completo) — guia/tutorial do RM3, entrada v2065 do namco.bdi.

Substitui `RM3/ferramentas/guia.py` (P-28), cujo ENQUADRAMENTO de registro estava
rotacionado em 28 bytes: ele lia os offsets de string nas posicoes absolutas
certas (por isso as strings sairam legiveis) mas atribuia os campos +8..+32 ao
registro seguinte. Ver `relatorio.md`.

Layout (little-endian), com `count` = 211 nesta instancia:

    0x00  u32       count            numero de nos
    0x04  u32[7]    reservado        zeros neste dump — preservado verbatim
    0x20  count x registro de 36 bytes:
            +0   u16  id             == indice do registro
            +2   u16  parent         id do pai; 0xffff no no raiz (registro 0)
            +4   u32  A              NAO IDENTIFICADO — preservar verbatim
            +8   u32  filho_ini      indice (em u32) no pool de ordem
            +12  u32  filho_num      quantidade de filhos
            +16  u32  B              linhas do corpo = corpo.count('\\n') + 1
            +20  u32  C              NAO IDENTIFICADO (0/1) — preservar verbatim
            +24  u32  D              NAO IDENTIFICADO — preservar verbatim
            +28  u32  off_titulo     offset ABSOLUTO no arquivo
            +32  u32  off_corpo      offset ABSOLUTO no arquivo
    0x20+count*36   pool de ordem: (count-1) x u32, permutacao exata de
                    1..count-1; a lista de filhos de cada no e' a faixa
                    [filho_ini, filho_ini+filho_num)
    ...             pool de strings: os `count` titulos em ordem de registro e
                    depois os `count` corpos em ordem de registro. Cada string e'
                    EUC-JP terminada em NUL e o INICIO de cada uma e' alinhado a
                    4 bytes (enchimento com NUL).
    ...             enchimento de zeros ate o span reservado pelo indice do bdi
                    (multiplo de 2048)

`parse()` verifica quatro invariantes e recusa o arquivo que nao os cumpre:
  1. 0x20 + count*36 == inicio do pool de ordem
  2. o pool de ordem e' permutacao exata de 1..count-1
  3. as faixas (filho_ini, filho_num) particionam o pool de ordem sem sobra nem
     sobreposicao, e todo filho listado por X declara parent == X
  4. os 2*count offsets de string sao exatamente os que a regra de empacotamento
     produz (ordem de registro, NUL, alinhamento de 4)

`build(parse(x)) == x` byte a byte na unica instancia do formato (v2065).

Somente leitura sobre a ISO — nada aqui abre arquivo para escrita.
"""
import struct

NUL = b'\x00'
NL = b'\x0a'
ENC = 'euc_jp'
HDR = 0x20
REC = 36
NOPARENT = 0xffff


def _align4(x):
    return (x + 3) & ~3


def _cstr(data, off):
    z = data.find(NUL, off)
    if z < 0:
        raise ValueError('string sem NUL em %#x' % off)
    return data[off:z]


def _offsets_esperados(pool0, regs):
    """Offsets que a regra de empacotamento produz: titulos em ordem de registro,
    depois corpos em ordem de registro; NUL e inicio alinhado a 4."""
    offs, p = [], pool0
    for r in regs:
        offs.append(p)
        p = _align4(p + len(r['titulo']) + 1)
    for r in regs:
        offs.append(p)
        p = _align4(p + len(r['corpo']) + 1)
    return offs


def parse(data: bytes, strict=True):
    if len(data) < HDR:
        raise ValueError('curto demais')
    count = struct.unpack_from('<I', data, 0)[0]
    if not (0 < count < 100000) or HDR + count * REC > len(data):
        raise ValueError('count implausivel: %d' % count)
    hdr_resto = list(struct.unpack_from('<7I', data, 4))

    regs = []
    for i in range(count):
        o = HDR + i * REC
        idv, parent = struct.unpack_from('<HH', data, o)
        A, ci, cn, B, C, D, t_off, c_off = struct.unpack_from('<8I', data, o + 4)
        regs.append({'i': i, 'id': idv, 'parent': parent, 'A': A,
                     'filho_ini': ci, 'filho_num': cn, 'B': B, 'C': C, 'D': D,
                     't_off': t_off, 'c_off': c_off,
                     'titulo': _cstr(data, t_off), 'corpo': _cstr(data, c_off)})

    ord_off = HDR + count * REC
    pool0 = min(r['t_off'] for r in regs)
    if (pool0 - ord_off) % 4:
        raise ValueError('pool de ordem nao multiplo de 4')
    n_ord = (pool0 - ord_off) // 4
    ordem = list(struct.unpack_from('<%dI' % n_ord, data, ord_off)) if n_ord else []

    avisos = []

    # --- invariante 2: o pool de ordem e' permutacao de 1..count-1
    if set(ordem) != set(range(1, count)) or len(ordem) != count - 1:
        msg = 'pool de ordem nao e permutacao de 1..%d' % (count - 1)
        if strict:
            raise ValueError(msg)
        avisos.append(msg)

    # --- invariante 3: as faixas de filhos particionam o pool, e o pai casa
    cobertura = [None] * n_ord
    for r in regs:
        for k in range(r['filho_ini'], r['filho_ini'] + r['filho_num']):
            if not (0 <= k < n_ord):
                raise ValueError('faixa de filhos fora do pool no reg %d' % r['i'])
            if cobertura[k] is not None:
                raise ValueError('pool de ordem coberto duas vezes em %d' % k)
            cobertura[k] = r['id']
    if any(c is None for c in cobertura):
        msg = 'pool de ordem com posicao nao coberta'
        if strict:
            raise ValueError(msg)
        avisos.append(msg)
    for k, dono in enumerate(cobertura):
        if dono is None:
            continue
        fk = ordem[k]
        if regs[fk]['parent'] != dono:
            msg = 'filho %d listado por %d mas parent=%d' % (fk, dono, regs[fk]['parent'])
            if strict:
                raise ValueError(msg)
            avisos.append(msg)

    # --- invariante 4: os offsets de string sao os do empacotamento
    esperados = _offsets_esperados(pool0, regs)
    reais = [r['t_off'] for r in regs] + [r['c_off'] for r in regs]
    if esperados != reais:
        difs = [(k, hex(a), hex(b)) for k, (a, b) in enumerate(zip(esperados, reais)) if a != b]
        msg = '%d offsets de string fora do empacotamento: %s' % (len(difs), difs[:5])
        if strict:
            raise ValueError(msg)
        avisos.append(msg)

    fim = esperados[-1] + len(regs[-1]['corpo']) + 1
    cauda = data[_align4(fim):]
    return {'count': count, 'hdr_resto': hdr_resto, 'regs': regs,
            'ordem': ordem, 'ord_off': ord_off, 'pool_off': pool0,
            'fim_pool': _align4(fim), 'cauda': cauda, 'avisos': avisos}


# ---------- campo derivado ----------

def b_incoerentes(p):
    """Registros cujo campo B nao casa com o numero de linhas do proprio corpo.
    Vazio num arquivo intacto — B e' cache do conteudo."""
    return [r['i'] for r in p['regs'] if r['B'] != r['corpo'].count(NL) + 1]


def recalcular_B(p):
    """Refaz o cache de linhas. Obrigatorio depois de mexer em qualquer corpo."""
    for r in p['regs']:
        r['B'] = r['corpo'].count(NL) + 1
    return p


# ---------- escrita ----------

def build(p, checar_B=True) -> bytes:
    """Reconstroi o arquivo. Recalcula os 2*count offsets de string a partir do
    conteudo; preserva verbatim o cabecalho, os campos A/C/D, id/parent, o pool
    de ordem e a cauda de enchimento.

    RECUSA gravar B desatualizado (checar_B=True): B e' cache do numero de
    linhas do corpo, entao traduzir sem chamar `recalcular_B()` gravaria um
    valor mentiroso. Passe checar_B=False so para reproduzir bytes originais.
    """
    count = p['count']
    regs = p['regs']
    if len(regs) != count:
        raise ValueError('count != numero de registros')
    if checar_B:
        ruins = b_incoerentes(p)
        if ruins:
            raise ValueError('campo B (numero de linhas) desatualizado em %d registros: %s'
                             ' - chame recalcular_B() antes de build()' % (len(ruins), ruins[:8]))
    ord_off = HDR + count * REC
    pool0 = ord_off + len(p['ordem']) * 4
    offs = _offsets_esperados(pool0, regs)

    out = bytearray()
    out += struct.pack('<I', count)
    out += struct.pack('<7I', *p['hdr_resto'])
    for k, r in enumerate(regs):
        out += struct.pack('<HH', r['id'], r['parent'])
        out += struct.pack('<8I', r['A'], r['filho_ini'], r['filho_num'],
                           r['B'], r['C'], r['D'], offs[k], offs[count + k])
    assert len(out) == ord_off, (len(out), ord_off)
    out += struct.pack('<%dI' % len(p['ordem']), *p['ordem'])
    assert len(out) == pool0
    for r in regs:
        out += r['titulo'] + NUL
        while len(out) % 4:
            out += NUL
    for r in regs:
        out += r['corpo'] + NUL
        while len(out) % 4:
            out += NUL
    out += p['cauda']
    return bytes(out)


def build_para_span(p, span: int, checar_B=True) -> bytes:
    """Como build(), mas re-enche com zeros ate `span` — o espaco que o indice do
    bdi reservou para a entrada — em vez de repetir a cauda original.
    RECUSA se o conteudo nao couber: crescer alem do span invadiria a entrada
    seguinte do bdi, e nao existe reconstrutor de indice no projeto.
    """
    p2 = dict(p)
    p2['cauda'] = b''
    corpo = build(p2, checar_B=checar_B)
    if len(corpo) > span:
        raise ValueError('conteudo %d B nao cabe no span de %d B (excesso %d B)'
                         % (len(corpo), span, len(corpo) - span))
    return corpo + NUL * (span - len(corpo))


def round_trip_ok(data: bytes) -> bool:
    return build(parse(data)) == data


def tamanho_projetado(p) -> int:
    """Tamanho que build() produziria sem a cauda de enchimento."""
    count = p['count']
    pool0 = HDR + count * REC + len(p['ordem']) * 4
    offs = _offsets_esperados(pool0, p['regs'])
    return _align4(offs[-1] + len(p['regs'][-1]['corpo']) + 1)


def decode(s: bytes) -> str:
    return s.decode(ENC)


def encode(t: str) -> bytes:
    return t.encode(ENC)

#!/usr/bin/env python3
"""Gera as linhas extra que faltam pro `guarda 2` do `eboot_build2.py` fechar
limpo no banco de item/equipamento (P-67.10).

`item_equip_extrai.py` varreu so' texto com kana/kanji dentro de cada faixa
de categoria — mas a faixa (do sentinela `無効値（categoria）` ate' o proximo)
tambem contem coisa que NAO e' esse tipo de texto e que precisa ser tratada
antes do build:

  1. o proprio sentinela `無効値（categoria）` de cada uma das 34 categorias
     (pulado de proposito na extracao, P-67.4) — e' referenciado por ponteiro
     de verdade (o registro de ID 0 = "nenhum"), precisa de traducao.
  2. campos de string VAZIA (`\0` imediato) — varios por categoria, ponteiro
     de "sem descricao"/"sem nome". Verbatim (fica vazio).
  3. punhado de casos isolados sem kana/kanji que por isso escaparam do
     filtro (`？？？`, `Ｅｍｐｔｙ`) — tratados individualmente abaixo.
  4. um ponteiro pra DENTRO de outra string ja capturada (sufixo, nao inicio)
     e um byte de controle solto — verbatim, mantem o byte original.

Achado rodando `eboot_build2.py --aplicar-nao` (dry-run) com TODOS os lotes
aprovados + o novo lote de item/equipamento: guarda 2 listou 448 ponteiros
de fora apontando pra dentro de alguma arena — agrupados, sao so' 201
strings distintas (a maioria, sentinela + vazio). Ver P-67.10.

NAO cobre a tabela de codigo de personagem (`cless`,`chester`,`none`...)
achada dentro da faixa de `foot_equip` (0x08C92FF8-0x08C934C8) — aquilo NAO
e' texto, e' dado interno (nome de asset), tratado à parte com o split de
`foot_equip` em `item_equip_split_foot.py`.

Uso: item_equip_extras.py <eboot_dec> [--saida CSV]
"""
import sys, csv, struct, argparse

DELTA = 0x08803000

# (bloco, va_string, texto_original) -> traducao explicita (None = verbatim)
TRADUCOES_MANUAIS = {
    '？？？': '???',
    'Ｅｍｐｔｙ': 'Empty',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eboot')
    ap.add_argument('--saida', default='dados/item_equip_extras.csv')
    args = ap.parse_args()

    raw = open(args.eboot, 'rb').read()

    sys.path.insert(0, 'ferramentas')
    from item_equip_extrai import CATEGORIAS, FIM_ULTIMA
    arenas = []
    nome_en_por_cena = {}
    for i, (jp, cena, en, va_ini) in enumerate(CATEGORIAS):
        va_fim = CATEGORIAS[i + 1][3] if i + 1 < len(CATEGORIAS) else FIM_ULTIMA
        arenas.append((cena, va_ini, va_fim))
        nome_en_por_cena[cena] = en

    # faixa da tabela de codigo de personagem dentro de foot_equip — excluida
    FURO_FOOT = (0x08C92FF8, 0x08C934C8)

    do_lote = set()
    import glob
    with open('dados/item_equip_ponteiros_limpo.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            do_lote.add(int(r['va_string'], 16))

    ELF_FIM = 5862704
    intrusos = []
    for q in range(0, ELF_FIM - 3, 4):
        w, = struct.unpack_from('<I', raw, q)
        for nome, a, fi in arenas:
            if a <= w < fi and w not in do_lote:
                intrusos.append((q + DELTA, w, nome))

    grupos = {}
    for vp, w, nome in intrusos:
        if nome == 'foot_equip' and FURO_FOOT[0] <= w < FURO_FOOT[1]:
            continue  # tabela de codigo de personagem — nunca tocar
        grupos.setdefault((nome, w), []).append(vp)

    saida = []
    for (nome, w), vps in sorted(grupos.items()):
        off = w - DELTA
        chunk = raw[off:off + 200]
        z = chunk.find(b'\x00')
        txt_bytes = chunk[:z] if z != -1 else chunk
        try:
            txt = txt_bytes.decode('euc_jp')
        except UnicodeDecodeError:
            txt = None

        if txt is not None and txt.startswith('無効値（'):
            # registro de ID 0 = "vazio" (slot sem item equipado) — usa a
            # mesma convencao curta ja' fechada noutras frentes do projeto
            # (P-67.7) em vez de traduzir literalmente "Valor Invalido", que
            # so' custaria byte sem trazer nada pro jogador
            trad = 'None'
            bytes_jp = len(txt_bytes)
        elif txt == '':
            trad = '(verbatim)'
            bytes_jp = 0
        elif txt in TRADUCOES_MANUAIS:
            trad = TRADUCOES_MANUAIS[txt]
            bytes_jp = len(txt_bytes)
        else:
            # sufixo de string ja capturada, byte de controle solto, ou
            # qualquer outra coisa nao reconhecida — mantem original
            trad = '(verbatim)'
            bytes_jp = len(txt_bytes)

        for vp in vps:
            saida.append({
                'bloco': nome, 'va_ponteiro': f'0x{vp:08X}', 'va_string': f'0x{w:08X}',
                'bytes_jp': bytes_jp, 'traducao': trad,
                'original': txt if txt is not None else repr(txt_bytes),
            })

    cols = ['bloco', 'va_ponteiro', 'va_string', 'bytes_jp', 'traducao', 'original']
    with open(args.saida, 'w', newline='', encoding='utf-8') as fh:
        w_ = csv.DictWriter(fh, fieldnames=cols)
        w_.writeheader()
        for r in saida:
            w_.writerow(r)

    print(f'{len(intrusos)} ponteiros intrusos originais, {len(grupos)} strings distintas '
          f'(excluida a faixa de codigo de personagem de foot_equip, {FURO_FOOT})')
    print(f'-> {len(saida)} linhas em {args.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

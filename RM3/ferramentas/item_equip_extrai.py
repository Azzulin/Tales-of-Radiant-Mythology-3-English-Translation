#!/usr/bin/env python3
"""Extrai o banco de item/equipamento inteiro do EBOOT (P-67.4) para lote.

Uso: item_equip_extrai.py <eboot_dec> <saida.tsv>

Formato achado em P-67.3/67.4: 34 categorias (5 de equipamento, 6 de item/
material, 23 tipos de arma — uma por classe jogável), cada uma um array de
REGISTROS DE TAMANHO FIXO POR CATEGORIA (confirmado: 24 B pra `消費アイテム`,
52 B pra `頭装備` — categorias diferentes, tamanhos diferentes, nao decifrado
pra todas as 34 ainda). Cada categoria comeca com uma entrada sentinela
`無効値（<categoria>）` ("valor invalido", o item de ID 0 = "nenhum").

Como o formato de registro NAO esta' fechado pra todas as categorias, esta
ferramenta NAO segue ponteiro — ela varre os BYTES BRUTOS dentro da faixa de
cada categoria (do inicio de uma sentinela ate' o inicio da proxima) atras de
toda substring terminada em NUL que decodifique limpo em EUC-JP e contenha
kana/kanji. Isso e' suficiente pra um lote de TRADUCAO (o tradutor so' precisa
do texto original) mas NAO resolve reinsercao — a ferramenta de build (que
precisa saber o ponteiro de cada string) fica para quando o registro de cada
categoria for decifrado, provavelmente por grupo (equipamento vs arma vs
item), nao tabela a tabela.

Dedup por string identica DENTRO da mesma categoria (mesma convencao de
sempre, P-42.3/P-54); residuo tecnico puro (nome de arquivo tipo `wmbg00.ppt`,
id interno) e' descartado pelo mesmo criterio de sempre — nao decodifica como
japones de verdade.

Somente leitura no binario.
"""
import sys, csv, struct, unicodedata

DELTA = 0x08803000

# nome da categoria (jp) -> (nome_en, va_inicio) — o FIM de cada uma e' o
# INICIO da proxima (ou +4200B pra ultima, 帯/Sash). Enderecos conferidos
# byte a byte nesta sessao (P-67.4), achados buscando toda ocorrencia de
# "無効値（" no binario inteiro.
CATEGORIAS = [
    ('頭装備', 'head_equip', 'Head Equipment', 0x08C64ADC),
    ('顔装備', 'face_equip', 'Face Equipment', 0x08C6CD4C),
    ('体装備', 'body_equip', 'Body Equipment', 0x08C6E7C8),
    ('手装備', 'hand_equip', 'Hand Equipment', 0x08C77794),
    ('足装備', 'foot_equip', 'Foot Equipment', 0x08C7F68C),
    ('消費アイテム', 'consumable', 'Consumable Item', 0x08C9F0A0),
    ('生産素材', 'craft_material', 'Crafting Material', 0x08C9F57C),
    ('強化素材', 'enhance_material', 'Enhancement Material', 0x08C9FB08),
    ('交換アイテム', 'exchange_item', 'Exchange Item', 0x08CA165C),
    ('アクセサリ', 'accessory', 'Accessory', 0x08CA3264),
    ('貴重品', 'valuables', 'Valuables', 0x08CA3ED8),
    ('片手剣', 'sword_1h', 'One-Handed Sword', 0x08CBFA78),
    ('両手剣', 'sword_2h', 'Two-Handed Sword', 0x08CC2828),
    ('短剣', 'dagger', 'Dagger', 0x08CC3DF4),
    ('斧', 'axe', 'Axe', 0x08CC55C0),
    ('杖', 'staff', 'Staff', 0x08CC6BC4),
    ('拳', 'fist', 'Fist', 0x08CC8AA8),
    ('弓', 'bow', 'Bow', 0x08CCAAE0),
    ('拳銃', 'handgun', 'Handgun', 0x08CCC3D0),
    ('槍', 'spear', 'Spear', 0x08CCDA50),
    ('トンファ', 'tonfa', 'Tonfa', 0x08CCE1F4),
    ('戦輪', 'chakram', 'Chakram', 0x08CCEA1C),
    ('ハンマー', 'hammer', 'Hammer', 0x08CCF1D0),
    ('ライフル', 'rifle', 'Rifle', 0x08CCFA84),
    ('バトン', 'baton', 'Baton', 0x08CD02E8),
    ('ボウガン', 'crossbow', 'Crossbow', 0x08CD0B1C),
    ('バッグ', 'bag', 'Bag', 0x08CD1338),
    ('剣玉', 'kendama', 'Kendama', 0x08CD1B2C),
    ('清掃具', 'cleaning_tool', 'Cleaning Tool', 0x08CD22BC),
    ('おたま', 'ladle', 'Ladle', 0x08CD2A8C),
    ('笛', 'flute', 'Flute', 0x08CD32EC),
    ('符', 'talisman', 'Talisman', 0x08CD3B44),
    ('ストロー', 'straw', 'Straw', 0x08CD433C),
    ('ペン', 'pen', 'Pen', 0x08CD4B8C),
    ('帯', 'sash', 'Sash', 0x08CD5450),
]
FIM_ULTIMA = 0x08CD5450 + 4200  # 帯/Sash nao tem categoria seguinte pra delimitar


def jp(c):
    return '\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff'


def eh_traduzivel(t):
    if not t.strip():
        return False
    if not any(jp(c) for c in t):
        return False
    # rejeita binario/tabela-de-registro que por coincidencia decodifica como
    # EUC-JP valido com kana/kanji — texto de verdade nao tem controle C0
    # (0x00-0x1F) fora de \n/\t, que ja viram \\n/\\t antes de chegar aqui
    # (achado ao rodar em `foot_equip`, P-67.7 — mesma familia do "sondador"
    # de P-39.5: contagem/decode sozinhos nao provam que e' texto).
    if any(unicodedata.category(c) == 'Cc' and c not in '\r\n\t' for c in t):
        return False
    return True


def main():
    eb, saida = sys.argv[1], sys.argv[2]
    raw = open(eb, 'rb').read()

    linhas = []
    resumo = []
    for i, (nome_jp, cena, nome_en, va_ini) in enumerate(CATEGORIAS):
        va_fim = CATEGORIAS[i + 1][3] if i + 1 < len(CATEGORIAS) else FIM_ULTIMA
        off_ini, off_fim = va_ini - DELTA, va_fim - DELTA
        blob = raw[off_ini:off_fim]

        vistos = {}
        ordem = 0
        p = 0
        while p < len(blob):
            z = blob.find(b'\x00', p)
            if z == -1:
                break
            chunk = blob[p:z]
            p = z + 1
            if not chunk:
                continue
            try:
                t = chunk.decode('euc_jp')
            except UnicodeDecodeError:
                continue
            if t.startswith('無効値（'):
                continue  # sentinela da propria categoria, id 0 = "nenhum"
            if not eh_traduzivel(t):
                continue
            va_string = off_ini + (p - len(chunk) - 1) + DELTA
            if t in vistos:
                vistos[t]['va_strings'].append(f'0x{va_string:08X}')
                continue
            row = {
                'id': f'{cena}#{ordem}', 'cena': cena, 'ordem': ordem,
                'falante_jp': '(item/equipamento)', 'falante_en': '(item/equipment)',
                'tipo': 'sistema', 'control_codes': '',
                'original': t.replace('\r\n', '\\n').replace('\n', '\\n').replace('\t', '\\t'),
                'traducao': '', 'nota_do_tradutor': '',
                'va_strings': [f'0x{va_string:08X}'],
                'categoria_en': nome_en,
            }
            vistos[t] = row
            linhas.append(row)
            ordem += 1
        resumo.append((cena, nome_en, ordem))

    for r in linhas:
        r['ocorrencias'] = len(r['va_strings'])
        r['va_strings'] = ';'.join(r['va_strings'])

    cols = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor',
            'va_strings', 'ocorrencias', 'categoria_en']
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter='\t')
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'{len(linhas)} linhas para traduzir -> {saida}\n')
    print(f'{"categoria":<18}{"nome_en":<24}{"distintas":>10}')
    total = 0
    for cena, nome_en, n in resumo:
        print(f'{cena:<18}{nome_en:<24}{n:>10}')
        total += n
    print(f'\nTOTAL: {total} strings distintas em {len(CATEGORIAS)} categorias')
    return 0


if __name__ == '__main__':
    sys.exit(main())

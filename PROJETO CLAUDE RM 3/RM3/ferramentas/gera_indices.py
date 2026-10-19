#!/usr/bin/env python3
"""Gera INDICE_NOMES.md e INDICE_TERMOS.md para o pacote do tradutor. Ver P-48.

Uso: gera_indices.py <elenco_falantes.csv> <termos_ui_guia.csv> <mev_falantes.csv> <dir_saida>

Os nomes vem do elenco medido no EBOOT (114) mais uma lista de topominos e
termos de mundo. Os termos vem do lexico do guia (P-40) filtrado para o que
aparece em dialogo de historia.
"""
import sys, csv, os, re, collections

MUNDO = [
    # jp, en, status, nota
    ('世界樹', 'World Tree', 'validado', 'termbase RM2'),
    ('ディセンダー', 'Descender', 'validado', 'canon da serie Radiant Mythology'),
    ('アドリビトム', 'Ad Libitum', 'validado', 'a guilda dos protagonistas; canon da serie'),
    ('バンエルティア号', 'Van Eltia', 'validado', 'termbase RM2; a nave-base'),
    ('ギルド', 'guild', 'validado', 'termbase RM2, minusculo quando comum'),
    ('マナ', 'mana', 'validado', 'termbase RM2, minusculo'),
    ('秘奥義', 'Mystic Arte', 'validado', 'termbase RM2'),
    ('術技', 'artes', 'validado', 'termbase RM2'),
    ('ガルド', 'Gald', 'validado', 'termbase RM2, a moeda'),
    ('クエスト', 'quest', 'validado', 'termbase RM2'),
    ('星晶', 'Star Crystal', 'revisar', 'RECURSO CENTRAL DO MUNDO, aparece em quest apos quest. Literal: cristal-estrela. Sem entrada no termbase RM2 — DECIDIR ANTES DE TUDO'),
    ('ルミナシア', 'Luminasia', 'revisar', 'o nome do mundo. Grafia provavel, confirmar'),
    ('ドクメント', 'Document', 'revisar', '115 ocorrencias na historia. Elemento de trama, nao palavra comum — grafar com maiuscula'),
    ('暁の従者', 'Servants of the Dawn', 'revisar', 'a seita antagonista; 15 ocorrencias entre parenteses angulares'),
    ('ヒトの祖', 'Progenitor of Man', 'revisar', '14 ocorrencias; titulo/entidade'),
    ('ソウルアルケミー', 'Soul Alchemy', 'revisar', 'mecanica/conceito, 18 ocorrencias'),
    ('ウリズン帝国', 'Urizen Empire', 'revisar', 'o imperio antagonista'),
    ('グラニデ', 'Granide', 'revisar', 'mundo de origem da Kanonno Earhart (mev26_030)'),
    ('光の幾何学場', 'Geometry of Light', 'revisar', 'ponto de salvamento na dungeon (P-40)'),
    ('生命讃歌の間', 'Hall of the Ode to Life', 'revisar', 'local da trama'),
    ('ヴェラトローパ', 'Veratropa', 'revisar', '42 ocorrencias; grafia por confirmar'),
    ('ジルディア', 'Zirdia', 'revisar', '42 ocorrencias; grafia por confirmar'),
    ('ボルテックス', 'Vortex', 'revisar', ''),
    ('アルマナック', 'Almanac', 'revisar', 'ruina; `[00]バンエルティア号`..`[06]アルマナック遺跡`'),
]

TOPONIMOS = [
    ('ヘーゼル村', 'Hazel Village', 'revisar', 'aveleira — padrao de comida (J5)'),
    ('コンフェイト大森林', 'Confeito Great Forest', 'revisar', 'confeito, doce — padrao de comida'),
    ('ガルバンゾ国', 'Garbanzo', 'revisar', 'grao-de-bico — padrao de comida'),
    ('ブラウニー坑道', 'Brownie Mine', 'revisar', 'brownie — padrao de comida'),
    ('ミブナの里', 'Mibuna Village', 'revisar', 'mibuna, verdura japonesa — padrao de comida'),
    ('オルタータ火山', 'Alterata Volcano', 'revisar', ''),
    ('オルタ・ビレッジ', 'Olta Village', 'revisar', ''),
    ('ライマ', 'Lima', 'revisar', 'feijao-de-lima — padrao de comida'),
    ('ルバーブ', 'Rhubarb', 'revisar', 'ruibarbo — padrao de comida'),
    ('カダイフ', 'Kadaif', 'revisar', 'massa turca — padrao de comida'),
    ('ギベオン', 'Gibeon', 'revisar', 'meteorito real — padrao mineral'),
    ('コクヨウ', 'Kokuyo', 'revisar', '黒曜 = obsidiana; considerar "Obsidian"'),
    ('ケイブレックス', 'Cavelex', 'revisar', 'grafia por confirmar'),
    ('シフノ', 'Sifno', 'revisar', 'grafia por confirmar'),
    ('モラード', 'Morado', 'revisar', 'roxo em espanhol'),
    ('ユルング', 'Yurlung', 'revisar', 'grafia por confirmar'),
]


def main():
    elc, ui, mev, dst = sys.argv[1:5]
    os.makedirs(dst, exist_ok=True)
    elenco = list(csv.DictReader(open(elc, encoding='utf-8')))
    rows = list(csv.DictReader(open(mev, encoding='utf-8')))

    # quantas falas cada personagem tem na historia principal
    fal = collections.Counter(r['falante'] for r in rows)
    # quantas vezes cada termo de mundo aparece no dialogo
    def conta(jp):
        return sum(r['original'].count(jp) for r in rows)

    with open(os.path.join(dst, 'INDICE_NOMES.md'), 'w', encoding='utf-8') as fh:
        fh.write('# Índice de nomes — lista FECHADA\n\n')
        fh.write('Um nome que está aqui se escreve **exatamente** como está aqui (regra R5).\n')
        fh.write('Um nome que **não** está aqui: pare e escreva na `nota_do_tradutor`.\n\n')
        fh.write('`validado` = decidido, use. `revisar` = proposta, use mas sinalize se '
                 'discordar. `jogo` = o próprio jogo diz o nome numa fala.\n\n')
        fh.write('---\n\n## 1. Elenco — os 114 falantes\n\n')
        fh.write('Medido na tabela de elenco do executável. `falas` = quantas falas o personagem '
                 'tem na história principal; 0 = não fala na história.\n\n')
        fh.write('| Japonês | **Nome adotado** | Jogo de origem | Falas | Fonte |\n')
        fh.write('|---|---|---|---|---|\n')
        for r in sorted(elenco, key=lambda r: -fal.get(r['nome_jp'], 0)):
            n = fal.get(r['nome_jp'], 0)
            fh.write(f'| `{r["nome_jp"]}` | **{r["nome_en"]}** | {r["jogo_de_origem"]} | '
                     f'{n or "—"} | {r["fonte_nome"]} |\n')
        fh.write('\n> **O jogo de origem não vem da ROM** — é conhecimento da série Tales. '
                 'Ele está aqui porque esses personagens têm localização oficial em inglês, e é '
                 'essa voz que a tradução deve casar (regra R7).\n')
        fh.write('\n> **As quatro Kanonno são personagens distintas.** '
                 '`カノンノ` = Kanonno Grassvalley, a heroína do RM3 — ela mesma diz o nome em '
                 '`mev00_040`. `パスカ・カノンノ` = Pasca Kanonno (RM2), '
                 '`カノンノ・イアハート` = Kanonno Earhart (RM1), '
                 '`オリジナル・カノンノ` = Original Kanonno. Nunca troque uma pela outra.\n')

        fh.write('\n---\n\n## 2. Termos do mundo e da trama\n\n')
        fh.write('| Japonês | **Adotado** | Ocorrências | Estado | Nota |\n|---|---|---|---|---|\n')
        for jp, en, st, nt in sorted(MUNDO, key=lambda x: -conta(x[0])):
            fh.write(f'| `{jp}` | **{en}** | {conta(jp) or "—"} | {st} | {nt} |\n')

        fh.write('\n---\n\n## 3. Topônimos\n\n')
        fh.write('**Os topônimos deste jogo são nomes de comida, de propósito** (regra J5). '
                 'Preserve o padrão.\n\n')
        fh.write('| Japonês | **Adotado** | Ocorrências | Estado | Nota |\n|---|---|---|---|---|\n')
        for jp, en, st, nt in sorted(TOPONIMOS, key=lambda x: -conta(x[0])):
            fh.write(f'| `{jp}` | **{en}** | {conta(jp) or "—"} | {st} | {nt} |\n')

    # --- termos de jogo ---
    termos = list(csv.DictReader(open(ui, encoding='utf-8')))
    usados = [t for t in termos if conta(t['origem_jp']) > 0]
    with open(os.path.join(dst, 'INDICE_TERMOS.md'), 'w', encoding='utf-8') as fh:
        fh.write('# Índice de termos de jogo — lista FECHADA\n\n')
        fh.write('Colhidos do guia interno do próprio jogo (206 termos citados entre `「」`) e '
                 'filtrados para os que **aparecem no diálogo da história principal**.\n\n')
        fh.write('Regra R6: termo que está aqui se escreve exatamente como está aqui.\n\n')
        fh.write(f'| Japonês | **Adotado** | No diálogo | Estado | Nota |\n|---|---|---|---|---|\n')
        for t in sorted(usados, key=lambda t: -conta(t['origem_jp'])):
            fh.write(f'| `{t["origem_jp"]}` | **{t["canonico_en"]}** | '
                     f'{conta(t["origem_jp"])} | {t["status"]} | {t["nota"]} |\n')
        fh.write(f'\n{len(usados)} de {len(termos)} termos do léxico aparecem na história '
                 f'principal. Os outros {len(termos)-len(usados)} são de menu e item, e estão em '
                 f'`dados/termos_ui_guia.csv`.\n')
    print(f'INDICE_NOMES.md: 114 falantes + {len(MUNDO)} termos de mundo + '
          f'{len(TOPONIMOS)} topônimos')
    print(f'INDICE_TERMOS.md: {len(usados)} termos que aparecem no diálogo')


if __name__ == '__main__':
    main()

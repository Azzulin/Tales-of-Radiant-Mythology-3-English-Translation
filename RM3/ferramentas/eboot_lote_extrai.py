#!/usr/bin/env python3
"""Extrai blocos do EBOOT para um lote de traducao no formato dos MEV (P-54).

Uso: eboot_lote_extrai.py <eboot_dec> <saida.tsv> [bloco1 bloco2 ...]

Sem argumentos de bloco, processa TODOS os blocos de BLOCOS (comportamento
original, usado para gerar o SIS-01). Passando um ou mais nomes de bloco no
final da linha de comando, restringe a saida a apenas esses — usado para gerar
lotes adicionais (ex. SIS-02) sem duplicar blocos ja extraidos e validados em
lotes anteriores.

Le os enderecos fixos definidos em BLOCOS abaixo (cada um documentado em
PADROES_DESCOBERTOS.md P-54), decodifica EUC-JP, DEDUPLICA string identica
dentro do mesmo bloco (um ponteiro so' precisa de uma traducao — P-42.3), pula
entrada que ja e' ASCII puro (rotulo que ja esta' em ingles, nada a traduzir) e
escreve um .tsv com as MESMAS colunas de um lote MEV, para que
`valida_retorno.py --sem-largura` sirva sem modificacao.

Colunas extras (fora do padrao MEV, ignoradas pelo validador): `va_ponteiros`
(todos os enderecos que usam esta string, separados por `;` — todos precisam
ser repontados/reescritos na hora do build) e `ocorrencias` (quantos ponteiros).

Somente leitura no binario.
"""
import sys, csv
import eboot_tabsis as T

NUL = b'\x00'


def faixa(ini, n):
    return [ini + i * 4 for i in range(n)]


# Blocos cujas entradas NAO sao um unico intervalo contiguo (sao garimpadas de
# tabelas-hospede diferentes) — a "arena" de um intervalo continuo nao se aplica
# a eles: o espaco de verdade e' o de CADA tabela-hospede inteira, que tem muito
# mais strings do que as escolhidas aqui (P-54).
NAO_CONTIGUOS = {'avisos', 'quests_sistema'}

# Indices da tabela "quests" (0x08D83230, 85 entradas, P-45/P-54) ja garimpados
# para o bloco 'avisos' do SIS-01 — nao repetir aqui (ver investigacao P-NN).
_QUESTS_JA_EM_AVISOS = {41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 60, 69, 70, 71, 84}

# 'classes_descricao' (0x08D65B54, 16 entradas) NAO entra aqui: e' a MESMA frase
# (menos o sufixo "(Beginner)"/"(Intermediate)") ja traduzida e aprovada em
# dados/lote_criacao.csv ids 78-93 (P-54). Nao manda pro tradutor — deriva por
# script a partir da traducao que ja existe. Ver eboot_lote_deriva_classes.py.

# Cada bloco: nome -> lista de vaddrs de ponteiro (P-54 tem o levantamento)
BLOCOS = {
    'resultado_batalha': faixa(0x08D656C0, 30),
    'nomes_cidade': faixa(0x08D66BC4, 15),
    'nomes_masmorra_viagem': faixa(0x08D66E30, 13),
    'nomes_masmorra_quadro': faixa(0x08D861C0, 12),
    'itens': faixa(0x08CA5EB4, 252),
    'avisos': (
        [0x08D83230 + i * 4 for i in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 60, 69, 70, 71, 84)]
        + [0x08D66818 + i * 4 for i in (4, 5, 6, 7, 8)]
    ),
    # Restante da tabela "quests" (0x08D83230, 85 entradas) que NAO entrou em
    # 'avisos' do SIS-01: objetivos de missao, popups de confirmacao/progresso
    # e mensagens de gerenciamento de grupo ligadas a aceitar/cumprir quest.
    # Investigado para SIS-02 (ver PADROES_DESCOBERTOS.md P-NN). O bloco
    # 'equipamento' (0x08D660EC, 151 entradas) foi investigado junto e
    # descartado: e' so' rotulo de menu/filtro/ordenacao e campo de bestiario,
    # nao nome+descricao de arma-armadura — nao entra aqui.
    'quests_sistema': [
        0x08D83230 + i * 4 for i in range(85) if i not in _QUESTS_JA_EM_AVISOS
    ],
    # Achados em P-67 (21/09/2026), respondendo ao mantenedor jogando `en10` e achando
    # nome de monstro, nome de personagem no HUD de batalha e texto de menu de
    # batalha ainda em japones — nenhuma das tres tabelas abaixo tinha sido tocada
    # desde o levantamento das 95 tabelas em P-45.
    'monstros_materiais': faixa(0x08D86280, 63),
    'elenco_hud_batalha': faixa(0x08D833FC, 237),
    # O ponteiro 0x08D655D0 (usado numa primeira tentativa) NAO e' o inicio
    # real da tabela — e' so' onde uma varredura por conteudo (musica de
    # batalha) comecou a parecer familiar. O verdadeiro inicio deste bloco de
    # ponteiros contiguo e' 0x08D654BC (conferido: os 4 ponteiros ANTES dele,
    # 0x08D654A8..0x08D654B8, ja pertencem a 'dialogo_save', que termina bem
    # em 0x08CF4FA0 — nenhuma sobreposicao). O bloco vai ate' pouco antes de
    # 'resultado_batalha' (0x08D656C0, ja construido em SIS-01 — confirmado
    # ponteiro a ponteiro) — 129 entradas ao todo (mission/target/BGM de
    # batalha + a lista inteira dos 16 titulos da serie Tales + "selecione
    # entre os temas de batalha de <jogo>" pra cada um). Pegar so' um pedaco
    # deste bloco (como a 1a tentativa fez) deixa RESIDUO destraduzido que
    # divide a MESMA arena de string com o pedaco que foi extraido — faria
    # eboot_build2.py recusar por ponteiro de fora apontando pra dentro da
    # arena (mesma licao do merge de SIS-03, P-66; achado rodando o build de
    # verdade, nao a auditoria isolada — sempre rode os dois).
    'menu_batalha': faixa(0x08D654BC, 129),
}


def decodifica(b):
    try:
        return b.decode('euc_jp')
    except UnicodeDecodeError:
        return b.decode('shift_jis')


def eh_ascii_puro(s):
    try:
        s.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False


def main():
    eb, saida = sys.argv[1], sys.argv[2]
    filtro = sys.argv[3:]
    blocos = {k: v for k, v in BLOCOS.items() if k in filtro} if filtro else BLOCOS
    if filtro:
        faltando = set(filtro) - set(BLOCOS)
        if faltando:
            print(f'bloco(s) desconhecido(s) em BLOCOS: {sorted(faltando)}')
            return 1
    d = T.ler(eb)

    linhas = []
    pulados = []
    resumo = []
    for bloco, vas in blocos.items():
        vistos = {}   # bytes originais -> linha (para dedup)
        ordem = 0
        arena_ents = []
        for va in vas:
            e = T.entradas(d, va, 1)[0]
            if e['off'] is None:
                pulados.append(f'{bloco} 0x{va:08X}: nao e ponteiro')
                continue
            arena_ents.append(e)
            jp = decodifica(e['original'])
            if eh_ascii_puro(jp):
                pulados.append(f'{bloco} 0x{va:08X}: ja e ASCII ({jp!r}), nada a traduzir')
                continue
            if jp in vistos:
                vistos[jp]['va_ponteiros'].append(f'0x{va:08X}')
                continue
            cc = ' '.join(sorted(set(
                ([f'%s x{jp.count("%s")}'] if '%s' in jp else []) +
                ([f'%d x{jp.count("%d")}'] if '%d' in jp else []) +
                ([f'LF x{jp.count(chr(10))}'] if '\n' in jp else []) +
                ([f'TAB x{jp.count(chr(9))}'] if '\t' in jp else []))))
            row = {
                'id': f'{bloco}#{ordem}', 'cena': bloco, 'ordem': ordem,
                'falante_jp': '(sistema)', 'falante_en': '(system)',
                'tipo': 'sistema', 'control_codes': cc,
                # \t escapado tambem: o arquivo e' TSV, um tab literal no campo
                # quebraria as colunas (achado ao extrair, ver 'classes_descricao#4')
                'original': jp.replace('\n', '\\n').replace('\t', '\\t'), 'traducao': '',
                'nota_do_tradutor': '',
                'va_ponteiros': [f'0x{va:08X}'],
            }
            vistos[jp] = row
            linhas.append(row)
            ordem += 1
        if bloco in NAO_CONTIGUOS:
            a_tam = None
        else:
            _, _, a_tam = T.arena(arena_ents) if arena_ents else (0, 0, 0)
        resumo.append((bloco, len(vas), len(vistos), a_tam))

    for r in linhas:
        r['ocorrencias'] = len(r['va_ponteiros'])
        r['va_ponteiros'] = ';'.join(r['va_ponteiros'])

    cols = ['id', 'cena', 'ordem', 'falante_jp', 'falante_en', 'tipo',
            'control_codes', 'original', 'traducao', 'nota_do_tradutor',
            'va_ponteiros', 'ocorrencias']
    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter='\t')
        w.writeheader()
        for r in linhas:
            w.writerow(r)

    print(f'{len(linhas)} linhas para traduzir -> {saida}\n')
    print(f'{"bloco":<24}{"ponteiros":>10}{"distintas":>11}{"arena(B)":>10}')
    for bloco, n, dist, tam in resumo:
        tam_str = 'n/a*' if tam is None else str(tam)
        print(f'{bloco:<24}{n:>10}{dist:>11}{tam_str:>10}')
    if any(tam is None for _, _, _, tam in resumo):
        print('* garimpado de tabelas-hospede maiores — arena e\' a da tabela inteira, nao so\' '
              'das linhas escolhidas aqui')
    if pulados:
        print(f'\npulados ({len(pulados)}), nao entram no lote:')
        for p in pulados:
            print('  ' + p)
    return 0


if __name__ == '__main__':
    sys.exit(main())

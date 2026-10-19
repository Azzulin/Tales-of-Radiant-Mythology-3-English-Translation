#!/usr/bin/env python3
"""Atribuicao de falante nas cenas FaceChat. Ver P-47.

O stream de comandos e' segmentado por 0xFFFF. O comando de exibir fala e'

    006B  <ator>  <indice_da_string>  <voz>  <banco_de_voz>  <t1>  <t2>

e **`falante = elenco[ator - 1]`** — o ID do ator e' 1-based sobre a tabela de
elenco do EBOOT em 0x08D66EB0 (114 nomes). Ator fora da faixa e' narracao ou
ator especial (203 = narracao, medido).

Somente leitura.
"""
import struct

OP_FALA = 0x006B     # <ator> <idx> <voz> <banco> <t1> <t2>, e' o rabo do segmento
N_ARGS_FALA = 6
OP_ESCOLHA = 0x0072  # <idx> <idx> ... — opcoes de dialogo que o jogador escolhe
OP_SISTEMA = 0x035D  # <idx> — mensagem de sistema / tutorial
OP_GRITO = 0x0075    # <idx> <banco> ... — fala sem caixa de nome
ATOR_NARRACAO = 203


def _texto_de_jogador(b):
    """Discriminador: a string parece texto que o jogador le?

    Exige japones (kana ou kanji) e recusa o que e' claramente tecnico. Usado
    SO para os opcodes sem campo de ator, onde nao ha prova de exibicao."""
    try:
        t = b.decode('euc_jp')
    except UnicodeDecodeError:
        return False
    if not t.strip():
        return False
    if all(ord(c) < 0x80 for c in t):
        return False
    return any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in t)


def comandos(tokens, n_tok):
    tok = list(struct.unpack_from(f'<{n_tok}H', tokens, 0))
    cmds, cur = [], []
    for t in tok:
        if t == 0xFFFF:
            cmds.append(cur); cur = []
        else:
            cur.append(t)
    if cur:
        cmds.append(cur)
    return cmds


def falas(p, elenco):
    """Devolve lista de dicts na ORDEM DA CENA: ordem, ator, falante, idx, texto.

    `elenco` = {indice0: nome}. Uma mesma string pode ser exibida mais de uma vez;
    cada exibicao entra como uma fala, com `repetida` marcando as depois da 1a.
    """
    ss = p['strings']
    out = []
    vistos = set()
    for c in comandos(p['tokens'], p['n_tok']):
        # O 0xFFFF termina SO o comando de fala. Outros comandos vem antes dele
        # no mesmo segmento, com contagem fixa de argumentos. Logo o comando de
        # fala e' o RABO do segmento: 006B + exatamente 6 palavras. Ver P-47.
        if len(c) < 1 + N_ARGS_FALA or c[-(1 + N_ARGS_FALA)] != OP_FALA:
            continue
        ator, idx = c[-N_ARGS_FALA], c[-N_ARGS_FALA + 1]
        if not (0 <= idx < len(ss)):
            continue
        try:
            texto = ss[idx].decode('euc_jp')
        except UnicodeDecodeError:
            continue
        if ator == ATOR_NARRACAO:
            falante, tipo = '(narracao)', 'narracao'
        elif 1 <= ator <= len(elenco):
            falante, tipo = elenco[ator - 1], 'personagem'
        else:
            falante, tipo = f'(ator {ator})', 'desconhecido'
        out.append({'ordem': len(out), 'ator': ator, 'falante': falante,
                    'tipo': tipo, 'idx': idx, 'bytes': len(ss[idx]),
                    'texto': texto, 'repetida': idx in vistos, 'opcode': OP_FALA})
        vistos.add(idx)

    # --- opcodes sem campo de ator ---
    # Ordem: estes entram DEPOIS, com a ordem original preservada em `ordem_bruta`,
    # porque nao ha como intercalar sem decodificar o fluxo inteiro. Ver P-47.
    extras = []
    for c in comandos(p['tokens'], p['n_tok']):
        for j, w in enumerate(c):
            if w == OP_ESCOLHA:
                k = j + 1
                grupo = []
                while k < len(c) and 0 <= c[k] < len(ss) and _texto_de_jogador(ss[c[k]]):
                    grupo.append(c[k]); k += 1
                for idx in grupo:
                    extras.append((idx, 'escolha', '(opcao do jogador)', OP_ESCOLHA))
            elif w == OP_SISTEMA and j + 1 < len(c):
                idx = c[j + 1]
                if 0 <= idx < len(ss) and _texto_de_jogador(ss[idx]):
                    extras.append((idx, 'sistema', '(mensagem de sistema)', OP_SISTEMA))
            elif w == OP_GRITO and j + 1 < len(c):
                idx = c[j + 1]
                if 0 <= idx < len(ss) and _texto_de_jogador(ss[idx]):
                    extras.append((idx, 'sem_caixa', '(sem caixa de nome)', OP_GRITO))
    for idx, tipo, falante, op in extras:
        if idx in vistos:
            continue
        vistos.add(idx)
        out.append({'ordem': len(out), 'ator': None, 'falante': falante,
                    'tipo': tipo, 'idx': idx, 'bytes': len(ss[idx]),
                    'texto': ss[idx].decode('euc_jp'), 'repetida': False,
                    'opcode': op})
    return out


def orfas(p, fs):
    """Strings que nenhum comando 006B exibe — nome de arquivo, nota de dev, etc."""
    usados = {f['idx'] for f in fs}
    out = []
    for i, s in enumerate(p['strings']):
        if i in usados:
            continue
        try:
            t = s.decode('euc_jp')
        except UnicodeDecodeError:
            t = s.hex()
        out.append({'idx': i, 'bytes': len(s), 'texto': t})
    return out

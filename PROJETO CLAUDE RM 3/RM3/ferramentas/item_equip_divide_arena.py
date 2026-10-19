#!/usr/bin/env python3
"""Divide um bloco em dois, para tirar de dentro da arena uma faixa de dados
INTERNOS que nao e' texto do lote (P-67.11).

Motivacao: `foot_equip` ocupa 0x08C7F68C..0x08C9EA3B (127919 B), mas no MEIO
dessa faixa mora a tabela de codigo de personagem (0x08C92FF8..0x08C934C8),
apontada por 154 ponteiros de fora do lote. A guarda 2 do `eboot_build2.py`
recusa (com razao) qualquer build cuja arena engula ponteiros externos: o pool
seria reempacotado por cima da tabela e o jogo leria lixo.

A arena de um bloco e' derivada das linhas daquele bloco (min va_string ate'
max va_string+bytes+1), entao a correcao NAO e' mexer na guarda: e' fazer o
bloco parar antes da faixa e recomecar depois dela. Como as strings do lote
estao todas fora da faixa (verificado: 0 dentro, 0 cruzando a borda), a divisao
e' exata e nao perde nenhuma string.

Uso:
  item_equip_divide_arena.py <csv> --bloco foot_equip \\
      --excluir 0x08C92FF8 0x08C934C8 [--saida CSV]

Recusa (sem escrever) se alguma string do bloco cair dentro da faixa ou cruzar
sua borda — nesse caso a divisao seria destrutiva e o caso precisa ser olhado
a mao.
"""
import sys, csv, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv_entrada')
    ap.add_argument('--bloco', required=True, help='nome do bloco a dividir')
    ap.add_argument('--excluir', nargs=2, required=True,
                    metavar=('INI', 'FIM'), help='faixa interna a deixar de fora')
    ap.add_argument('--saida', default=None, help='padrao: sobrescreve a entrada')
    args = ap.parse_args()

    t0, t1 = int(args.excluir[0], 16), int(args.excluir[1], 16)
    saida = args.saida or args.csv_entrada

    with open(args.csv_entrada, encoding='utf-8') as f:
        leitor = csv.DictReader(f)
        cols = leitor.fieldnames
        rows = list(leitor)

    alvo = [r for r in rows if r['bloco'] == args.bloco]
    if not alvo:
        print(f'ERRO: bloco {args.bloco} nao existe em {args.csv_entrada}')
        return 2

    # --- recusa se alguma string do lote encostar na faixa ---
    encosta = []
    for r in alvo:
        ini = int(r['va_string'], 16)
        fim = ini + int(r['bytes_jp']) + 1
        if ini < t1 and fim > t0:
            encosta.append(r)
    if encosta:
        print(f'RECUSADO: {len(encosta)} strings de {args.bloco} caem dentro da '
              f'faixa 0x{t0:08X}..0x{t1:08X} (ou cruzam sua borda)')
        for r in encosta[:10]:
            print(f'  0x{int(r["va_string"], 16):08X} +{r["bytes_jp"]} B  '
                  f'id={r.get("id", "?")}')
        return 1

    a = b = 0
    for r in alvo:
        if int(r['va_string'], 16) < t0:
            r['bloco'] = args.bloco + '_a'
            a += 1
        else:
            r['bloco'] = args.bloco + '_b'
            b += 1

    def faixa(nome):
        rs = [r for r in rows if r['bloco'] == nome]
        vs = [(int(r['va_string'], 16), int(r['bytes_jp'])) for r in rs]
        i, f = min(v for v, _ in vs), max(v + n + 1 for v, n in vs)
        return i, f, f - i

    for nome, n in ((args.bloco + '_a', a), (args.bloco + '_b', b)):
        i, f, tam = faixa(nome)
        print(f'  [{nome}] arena 0x{i:08X}..0x{f:08X} = {tam} B, {n} ponteiros')
    print(f'faixa excluida 0x{t0:08X}..0x{t1:08X} = {t1 - t0} B, '
          f'agora fora de toda arena')

    with open(saida, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f'-> {saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

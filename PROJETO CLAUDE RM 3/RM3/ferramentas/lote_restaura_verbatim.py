#!/usr/bin/env python3
"""Devolve o ingles as linhas `(verbatim)` de um lote do EBOOT (P-91).

`(verbatim)` foi o jeito de manter em japones uma string que nao cabia na arena
(`item_equip_cabe_ou_verbatim.py`, P-67.14) sem tirar o ponteiro do lote. Com o
segmento de transbordo (`eboot_build2.py --transborda`), o que nao cabe vai
para la: a traducao aprovada pode voltar.

So' mexe em linha `(verbatim)`, e so' quando a fonte tem para ela uma traducao
ASCII nao vazia e que nao e' ela mesma `(verbatim)`. A chave e' escolhida:
  --por va_ponteiro   a fonte e' um CSV de ponteiros (item_equip_ponteiros.csv);
                      exige tambem o mesmo `original`
  --por id            a fonte sao os `*_retorno.tsv` do P-68; `--sobrepor` aplica
                      os mesmos JSON de encurtamento que o `p68_para_lote.py`
Simbolo puro (glifo `○`, `→`) nao tem traducao na fonte e fica como esta.

Dry-run por padrao; `--aplicar` grava e deixa `*.bak_pre_p91`.

Uso:
  lote_restaura_verbatim.py <lote.csv> --por va_ponteiro --fonte <csv>
  lote_restaura_verbatim.py <lote.csv> --por id --fonte "lotes_p68/*_retorno.tsv"
                            [--sobrepor <json>...] [--aplicar]
"""
import sys, csv, io, glob, json, shutil, argparse, collections

VERB = '(verbatim)'
SUFIXO_BAK = '.bak_pre_p91'


def carrega_fonte(padroes, por):
    m = {}
    for pad in padroes:
        for p in sorted(glob.glob(pad)) or [pad]:
            delim = '\t' if p.lower().endswith('.tsv') else ','
            for r in csv.DictReader(open(p, encoding='utf-8'), delimiter=delim):
                t = (r.get('traducao') or '').strip()
                if not t or t == VERB:
                    continue
                m[r[por]] = (t, r.get('original'))
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lote')
    ap.add_argument('--por', required=True, choices=('va_ponteiro', 'id'))
    ap.add_argument('--fonte', required=True, nargs='+')
    ap.add_argument('--sobrepor', nargs='*', default=[])
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()

    fonte = carrega_fonte(a.fonte, a.por)
    over = {}
    for j in a.sobrepor:
        over.update(json.load(open(j, encoding='utf-8')))

    dado = open(a.lote, 'rb').read().decode('utf-8')
    fim = '\r\n' if '\r\n' in dado else '\n'
    linhas = list(csv.reader(io.StringIO(dado, newline='')))
    cab = linhas[0]
    it, ik = cab.index('traducao'), cab.index(a.por)
    io_ = cab.index('original') if 'original' in cab else None

    trocas, sem, nao_ascii, orig_dif = collections.Counter(), collections.Counter(), [], []
    novas = [cab]
    for r in linhas[1:]:
        r2 = list(r)
        if len(r2) > it and r2[it] == VERB:
            bloco = r2[0]
            k = r2[ik]
            if k in fonte:
                t, o = fonte[k]
                if a.por == 'id' and k in over:
                    t = over[k]
                if a.por == 'va_ponteiro' and io_ is not None and o is not None and o != r2[io_]:
                    orig_dif.append(k)
                elif not t.isascii():
                    nao_ascii.append(k)
                else:
                    r2[it] = t
                    trocas[bloco] += 1
            else:
                sem[bloco] += 1
        novas.append(r2)

    print('%s: %d linhas voltam ao ingles' % (a.lote, sum(trocas.values())))
    for b, c in trocas.most_common():
        print('   %-24s %d' % (b, c))
    if sem:
        print('sem traducao na fonte (ficam (verbatim)): %d — %s'
              % (sum(sem.values()), ', '.join('%s %d' % kv for kv in sem.most_common(6))))
    if orig_dif:
        print('RECUSADO: %d chaves com `original` diferente na fonte: %s' % (len(orig_dif), orig_dif[:5]))
        return 1
    if nao_ascii:
        print('RECUSADO: %d traducoes nao ASCII na fonte: %s' % (len(nao_ascii), nao_ascii[:5]))
        return 1

    out = io.StringIO(newline='')
    csv.writer(out, lineterminator=fim).writerows(novas)
    texto = out.getvalue()
    relido = list(csv.reader(io.StringIO(texto, newline='')))
    for x, y in zip(linhas, relido):
        if [v for i, v in enumerate(x) if i != it] != [v for i, v in enumerate(y) if i != it]:
            print('RECUSADO: reescrever o CSV mudaria outra coluna')
            return 1
    if not a.aplicar:
        print('DRY-RUN. Nada foi escrito. Rode de novo com --aplicar.')
        return 0
    if trocas:
        shutil.copy2(a.lote, a.lote + SUFIXO_BAK)
        open(a.lote, 'wb').write(texto.encode('utf-8'))
        print('gravado; copia anterior em %s' % (a.lote + SUFIXO_BAK))
    return 0


if __name__ == '__main__':
    sys.exit(main())

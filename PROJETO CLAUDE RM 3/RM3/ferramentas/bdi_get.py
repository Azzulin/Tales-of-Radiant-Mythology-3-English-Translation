#!/usr/bin/env python3
"""Extrai arquivos logicos do namco.bdi para um diretorio, pelo catalogo.

Uso:
  bdi_get.py <iso> <lba> <size> <catalogo.csv> <destino> <padrao_regex> [--dry-run]

Recebe: ISO (somente leitura) + catalogo gerado por bdi_catalog.py.
Devolve: um arquivo por linha do catalogo cujo nome casa com o regex.
Valida: recusa nome com '/', '\' ou '..'; recusa sobrescrever arquivo existente;
        confere que off+tamanho cabe no bdi.
Falha em seguranca: --dry-run por padrao de uso recomendado; nunca escreve na ISO.
"""
import sys, os, csv, re

SEC = 2048


def main():
    iso, lba, size, cat, dest, pat = sys.argv[1:7]
    lba, size = int(lba), int(size)
    dry = '--dry-run' in sys.argv
    rx = re.compile(pat, re.I)
    base = lba * SEC
    rows = [r for r in csv.DictReader(open(cat, encoding='utf-8')) if rx.search(r['nome'])]
    print(f'{len(rows)} linhas casam com /{pat}/')
    if not dry:
        os.makedirs(dest, exist_ok=True)
    n = skip = 0
    with open(iso, 'rb') as f:
        for r in rows:
            nome, sz, off = r['nome'], int(r['tamanho']), int(r['off_bdi'])
            if not nome or '/' in nome or '\\' in nome or '..' in nome:
                print(f'  RECUSADO nome invalido: {nome!r}'); skip += 1; continue
            if off + sz > size:
                print(f'  RECUSADO fora do bdi: {nome} off={off} sz={sz}'); skip += 1; continue
            out = os.path.join(dest, f"v{r['entrada_v']}_{nome}")
            if dry:
                print(f'  [dry] {out}  {sz} B  @0x{off:x}'); continue
            if os.path.exists(out):
                print(f'  ja existe, pulando: {out}'); skip += 1; continue
            f.seek(base + off)
            data = f.read(sz)
            if len(data) != sz:
                print(f'  RECUSADO leitura curta: {nome}'); skip += 1; continue
            with open(out, 'wb') as o:
                o.write(data)
            n += 1
    print(f'extraidos={n} pulados={skip}')


if __name__ == '__main__':
    main()

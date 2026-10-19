import csv, sys

def inspect(path, n=20):
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    print(f"File: {path}, Total rows: {len(rows)}")
    for i, r in enumerate(rows[:n]):
        print(f"[{i}] id={r['id']} orig={r['original']!r} b_jp={r.get('bytes_jp')} max_b={r.get('max_bytes')}")

if __name__ == '__main__':
    inspect(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20)

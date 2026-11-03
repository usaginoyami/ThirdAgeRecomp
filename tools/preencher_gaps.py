#!/usr/bin/env python3
"""Acrescenta ao CSV do Ghidra as funcoes que ele nao criou (trechos de .text sem cobertura).

O Ghidra deixa de fora funcoes minusculas (ex.: metodos virtuais vazios `jr $ra; nop`). O runtime
nao acha destino para uma chamada indireta a elas ("guest-branch:missing-target") e trava.
Aqui cada trecho descoberto e dividido em "funcoes" que terminam em `jr $ra` + delay slot.
Trechos so de nop (preenchimento de alinhamento) sao ignorados.

Uso:  python tools/preencher_gaps.py dados/SLUS_210.27 config/thirdage.ghidra.csv [saida.csv]
Sem 'saida', reescreve o CSV de entrada (guarda o original em *.orig.csv na primeira vez).
"""
import csv
import os
import shutil
import struct
import sys


def main():
    elf, csvp = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else csvp
    d = open(elf, "rb").read()
    shoff = struct.unpack_from("<I", d, 0x20)[0]
    es, num, si = struct.unpack_from("<HHH", d, 0x2E)
    raw = [struct.unpack_from("<IIIIII", d, shoff + i * es) for i in range(num)]
    so = raw[si][4]
    text = None
    for nm, ty, fl, ad, of, sz in raw:
        e = d.index(b"\0", so + nm)
        if d[so + nm:e] == b".text":
            text = (ad, of, sz)
    ad, of, sz = text
    rows = []
    with open(csvp, newline="") as f:
        for r in csv.reader(f):
            rows.append(r)
    header = rows[0] if rows and rows[0][0] == "Name" else None
    body = rows[1:] if header else rows
    if out == csvp and not os.path.exists(csvp.replace(".csv", ".orig.csv")):
        shutil.copy2(csvp, csvp.replace(".csv", ".orig.csv"))
    funcs = []
    for r in body:
        if r[0].startswith(("entry_", "caseD_")):
            continue
        funcs.append((int(r[1], 16), int(r[2], 16)))
    funcs.sort()
    gaps, last = [], ad
    for s, e in funcs:
        if s > last:
            gaps.append((last, s))
        last = max(last, e)
    if last < ad + sz:
        gaps.append((last, ad + sz))

    def w(a):
        return struct.unpack_from("<I", d, of + a - ad)[0]

    novas = []
    for g0, g1 in gaps:
        a = g0
        while a < g1:
            while a < g1 and w(a) == 0:  # nop de preenchimento
                a += 4
            if a >= g1:
                break
            b = a
            while b < g1:
                ins = w(b)
                b += 4
                if ins == 0x03E00008:  # jr $ra
                    b = min(b + 4, g1)  # delay slot
                    break
            novas.append((a, b))
            a = b
    for a, b in novas:
        body.append([f"FUN_{a:08x}", f"0x{a:08X}", f"0x{b:08X}", str(b - a)])
    body.sort(key=lambda r: (int(r[1], 16), r[0]))
    with open(out, "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        if header:
            wr.writerow(header)
        wr.writerows(body)
    print(f"{len(gaps)} trechos descobertos -> {len(novas)} funcoes acrescentadas; total {len(body)}")


if __name__ == "__main__":
    main()

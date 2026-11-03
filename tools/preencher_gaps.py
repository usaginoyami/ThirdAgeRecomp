#!/usr/bin/env python3
"""Acrescenta ao CSV do Ghidra as funcoes que ele nao criou (trechos de .text sem cobertura).

O Ghidra deixa de fora funcoes minusculas (ex.: metodos virtuais vazios `jr $ra; nop`). O runtime
nao acha destino para uma chamada indireta a elas ("guest-branch:missing-target") e trava.
Aqui cada trecho descoberto e dividido em "funcoes" que terminam em `jr $ra` + delay slot.
Trechos so de nop (preenchimento de alinhamento) sao ignorados.
Depois acrescenta `entry_` para alvos de chamada indireta que caem no meio de uma funcao do Ghidra
(ponteiros em dados, como vtables, e constantes lui+addiu/ori no codigo).

Uso:  python tools/preencher_gaps.py dados/SLUS_210.27 config/thirdage.ghidra.orig.csv config/thirdage.ghidra.csv
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

    # --- 2) alvos de chamada indireta: ponteiros em dados e constantes lui+addiu/ori em codigo ---
    tsec = (ad, ad + sz)
    alvos = set()
    for nm, ty, fl, a_, o_, s_ in raw:
        e = d.index(b"\0", so + nm)
        n = d[so + nm:e].decode()
        if ty != 1 or not (fl & 2) or n in (".text", ".vutext") or s_ < 4:
            continue  # so PROGBITS alocaveis de dados
        for k in range(0, s_ - 3, 4):
            v = struct.unpack_from("<I", d, o_ + k)[0]
            if tsec[0] <= v < tsec[1] and v % 4 == 0:
                alvos.add(v)
    ndados = len(alvos)
    n_ins = sz // 4
    for i in range(n_ins - 1):
        ins = w(ad + i * 4)
        if ins >> 26 != 0x0F:  # lui
            continue
        rt, hi = (ins >> 16) & 31, (ins & 0xFFFF) << 16
        if rt == 0:
            continue
        for j in range(i + 1, min(i + 8, n_ins)):
            nx = w(ad + j * 4)
            op, rs, rt2, imm = nx >> 26, (nx >> 21) & 31, (nx >> 16) & 31, nx & 0xFFFF
            if rs == rt and op in (0x09, 0x0D):  # addiu / ori
                v = (hi + (imm - 0x10000 if (op == 0x09 and imm & 0x8000) else imm)) & 0xFFFFFFFF
                if tsec[0] <= v < tsec[1] and v % 4 == 0:
                    alvos.add(v)
                break
            if rt2 == rt and op != 0x2B:  # registrador sobrescrito
                break
    print(f"alvos candidatos: {len(alvos)} (ponteiros em dados: {ndados})")
    # inicios ja conhecidos (funcoes e entradas)
    inicios = sorted({int(r[1], 16) for r in body})
    import bisect
    fl_ = sorted([(int(r[1], 16), int(r[2], 16)) for r in body if not r[0].startswith(("entry_", "caseD_"))])
    fstarts = [x[0] for x in fl_]
    conhecidos = set(inicios)
    novas_e = 0
    for t in sorted(alvos):
        if t in conhecidos:
            continue
        k = bisect.bisect_right(fstarts, t) - 1
        if k < 0 or not (fl_[k][0] <= t < fl_[k][1]):
            continue  # fora de qualquer funcao (nao deve ocorrer apos o preenchimento)
        fe = fl_[k][1]
        m = bisect.bisect_right(inicios, t)
        fim = min(fe, inicios[m]) if m < len(inicios) else fe
        body.append([f"entry_{t:08x}", f"0x{t:08X}", f"0x{fim:08X}", str(fim - t)])
        conhecidos.add(t)
        inicios = sorted(conhecidos)
        novas_e += 1
    print(f"entradas acrescentadas por ponteiro: {novas_e}")
    body.sort(key=lambda r: (int(r[1], 16), r[0]))
    with open(out, "w", newline="") as f:
        wr = csv.writer(f, lineterminator="\n")
        if header:
            wr.writerow(header)
        wr.writerows(body)
    print(f"{len(gaps)} trechos descobertos -> {len(novas)} funcoes acrescentadas; total {len(body)}")


if __name__ == "__main__":
    main()

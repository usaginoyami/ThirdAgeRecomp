#!/usr/bin/env python3
"""Census estatico dos microprogramas de VU1 de um ELF de PS2 (secao .vutext).

Uso:  python vu1_census.py dados/SLUS_210.27 [--json saida.json] [--dump pasta]

O linker da Sony/SN guarda o codigo de VU1 em .vutext como pacotes VIF: cada comando MPG
(cmd 0x4A: NUM pares de 64 bits + endereco de carga em unidades de 8 bytes) carrega um pedaco
de microcodigo na memoria do VU1. As secoes .DVP.overlay.* do ELF so descrevem esses pedacos
(nome = ..<endereco VU>.<id do programa>.<n>.<indice>) e vem zeradas no arquivo.

O script: (1) acha os pacotes MPG no .vutext; (2) confere com a tabela de overlays;
(3) agrupa os pedacos em programas; (4) classifica as instrucoes (E-bit, XGKICK, desvios, divisoes...).
Nao escreve nada do jogo (--dump grava os pedacos, so para analise local; nao versionar).
"""
import argparse
import collections
import json
import os
import re
import struct
import sys


def secoes(d):
    shoff = struct.unpack_from("<I", d, 0x20)[0]
    entsize, num, strndx = struct.unpack_from("<HHH", d, 0x2E)
    raw = [struct.unpack_from("<IIIIII", d, shoff + i * entsize) for i in range(num)]
    stroff = raw[strndx][4]
    out = []
    for name, typ, flags, addr, off, size in raw:
        e = d.index(b"\0", stroff + name)
        out.append((d[stroff + name:e].decode(), addr, off, size))
    return out


def acha_mpg(v):
    """Procura comandos MPG alinhados em 4 bytes. Retorna [(offset_do_cmd, num_pares, endereco_vu)]."""
    achados = []
    for o in range(0, len(v) - 4, 4):
        w = struct.unpack_from("<I", v, o)[0]
        if ((w >> 24) & 0x7F) != 0x4A:
            continue
        num = (w >> 16) & 0xFF or 256
        imm = w & 0xFFFF
        if o + 4 + num * 8 > len(v) or imm * 8 >= 0x4000:
            continue
        achados.append((o, num, imm * 8))
    return achados


def classifica(lo, up):
    """Conta recursos de um par (lower, upper) de VU1. Codificacoes conforme o manual do VU."""
    c = collections.Counter()
    if up & 0x40000000:
        c["E (fim de programa)"] += 1
    if up & 0x80000000:
        c["I (imediato no lower)"] += 1
    if up & 0x20000000:
        c["M (flag mac)"] += 1
    if up & 0x10000000:
        c["D (debug)"] += 1
    if up & 0x08000000:
        c["T (debug)"] += 1
    if not (up & 0x80000000):  # com I-bit o lower e um float imediato
        op = (lo >> 25) & 0x7F
        if op == 0x40:
            f = lo & 0x3F
            if f >= 0x3C:
                s = (lo & 3) | ((lo >> 4) & 0x7C)
                nomes = {0x6C: "XGKICK", 0x38: "DIV", 0x39: "SQRT", 0x3A: "RSQRT",
                         0x68: "XTOP", 0x69: "XITOP", 0x64: "MFP", 0x3B: "WAITQ", 0x7B: "WAITP",
                         0x40: "RNEXT", 0x41: "RGET", 0x42: "RINIT", 0x43: "RXOR"}
                if s in nomes:
                    c[nomes[s]] += 1
                elif 0x70 <= s <= 0x7E:
                    c["EFU (ESIN/EATAN/ERCPR...)"] += 1
        elif op in (0x20, 0x21):
            c["B/BAL"] += 1
        elif op in (0x24, 0x25):
            c["JR/JALR"] += 1
        elif op in (0x28, 0x29) or 0x2C <= op <= 0x2F:
            c["desvio condicional"] += 1
        elif op in (0x00, 0x04):
            c["LQ/ILW (load)"] += 1
        elif op in (0x01, 0x05):
            c["SQ/ISW (store)"] += 1
        elif 0x10 <= op <= 0x1C:
            c["flags (FC*/FS*/FM*)"] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("elf")
    ap.add_argument("--json")
    ap.add_argument("--dump")
    a = ap.parse_args()
    d = open(a.elf, "rb").read()
    sec = secoes(d)
    vut = next(s for s in sec if s[0] == ".vutext")
    v = d[vut[2]:vut[2] + vut[3]]
    mpgs = acha_mpg(v)

    ov = []
    for nome, addr, off, size in sec:
        m = re.match(r"\.DVP\.overlay\.\.(0x[0-9a-fA-F]+|unknvma)\.(\d+)\.(\d+)\.(\d+)", nome)
        if m:
            base, pid, n, idx = m.groups()
            ov.append(dict(base=None if base == "unknvma" else int(base, 16), id=pid, n=int(n),
                           idx=int(idx), size=size, zerado=not any(d[off:off + size])))

    print(f".vutext: {len(v)} bytes ({len(v) // 8} pares), {len(mpgs)} comandos MPG candidatos")
    print(f"overlays na tabela: {len(ov)} (todos zerados no ELF: {all(o['zerado'] for o in ov)})")

    # confere: cada overlay deve ter um MPG com mesmo endereco e tamanho
    casados, sem = 0, []
    usados = set()
    for o in ov:
        achou = None
        for i, (off, num, vaddr) in enumerate(mpgs):
            if i in usados:
                continue
            if num * 8 == o["size"] and (o["base"] is None or vaddr == o["base"]):
                achou = i
                break
        if achou is None:
            sem.append(o)
        else:
            usados.add(achou)
            casados += 1
            o["mpg"] = mpgs[achou]
    print(f"overlays casados com pacote MPG (endereco e tamanho): {casados}/{len(ov)}")
    for o in sem:
        print("  sem par:", o)

    # agrupa em programas: um programa novo comeca quando o endereco VU volta para 0
    ordenados = sorted((o for o in ov if "mpg" in o), key=lambda o: o["mpg"][0])
    progs, atual = [], []
    for o in ordenados:
        if o["mpg"][2] == 0 and atual:
            progs.append(atual)
            atual = []
        atual.append(o)
    if atual:
        progs.append(atual)

    resumo = []
    total = collections.Counter()
    print("\nprogramas (por ordem no .vutext):")
    for k, p in enumerate(progs):
        cnt = collections.Counter()
        pares = 0
        for o in p:
            off, num, vaddr = o["mpg"]
            base = off + 4
            for j in range(num):
                lo, up = struct.unpack_from("<II", v, base + j * 8)
                cnt.update(classifica(lo, up))
            pares += num
        total.update(cnt)
        fim = max(o["mpg"][2] + o["mpg"][1] * 8 for o in p)
        print(f"  P{k}: {len(p)} pedaco(s), {pares} pares, memoria VU ate 0x{fim:04X}, "
              f"id {p[0]['id']}, E-bit={cnt['E (fim de programa)']}, XGKICK={cnt['XGKICK']}, "
              f"JR={cnt['JR/JALR']}, desvios={cnt['desvio condicional'] + cnt['B/BAL']}")
        resumo.append(dict(programa=k, id=p[0]["id"], pedacos=[(hex(o["mpg"][2]), o["mpg"][1]) for o in p],
                           pares=pares, fim_vu=hex(fim), contagem=dict(cnt)))
        if a.dump:
            os.makedirs(a.dump, exist_ok=True)
            for o in p:
                off, num, vaddr = o["mpg"]
                open(os.path.join(a.dump, f"P{k}_{vaddr:04X}.bin"), "wb").write(v[off + 4:off + 4 + num * 8])

    # conteudo repetido entre programas (pedaco do endereco 0, o "prelude")
    pre = collections.Counter()
    for p in progs:
        o = p[0]
        off, num, _ = o["mpg"]
        pre[v[off + 4:off + 4 + num * 8]] += 1
    print(f"\npedacos iniciais (endereco 0) distintos: {len(pre)}; repeticoes: {sorted(pre.values(), reverse=True)}")
    print("\ninstrucoes (total):")
    for k_, n_ in total.most_common():
        print(f"  {k_:28} {n_}")
    if a.json:
        json.dump(dict(vutext_bytes=len(v), mpg=len(mpgs), casados=casados, programas=resumo,
                       total=dict(total)), open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()

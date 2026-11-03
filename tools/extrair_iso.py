#!/usr/bin/env python3
"""Extrai arquivos de um ISO9660 (disco de PS2), sem dependencias.

Uso:
  python extrair_iso.py "The Third Age.iso"            -> extracao seletiva (padrao)
  python extrair_iso.py "The Third Age.iso" --tudo     -> extrai o disco inteiro (~4,3 GB)
  python extrair_iso.py "The Third Age.iso" -o pasta   -> escolhe a pasta de saida

Extracao seletiva (cerca de 150 MB):
  - MODULES\\*, SLUS, SYSTEM.CNF, LOADONCE.SCP e GLOBSCEN.SCP: completos
  - E3C1F12.PS2 (menor filme): completo, para testar o decodificador
  - todos os outros arquivos: so o inicio (1 MB), salvo como <nome>.head
Alem disso grava mapa_lba.txt (caminho -> LBA/tamanho), pois o jogo le o disco
por LBA e o runtime precisa respeitar esse layout.
"""
import os
import struct
import sys

SECTOR = 2048
HEAD = 1024 * 1024
COMPLETOS = ("\\MODULES\\", "\\SLUS_", "\\SYSTEM.CNF", "\\DATA\\LOADONCE.SCP",
             "\\DATA\\GAME\\GLOBSCEN.SCP", "\\DATA\\MOVIES\\E3C1F\\E3C1F12.PS2")


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def le_dir(f, lba, size):
    f.seek(lba * SECTOR)
    data = f.read(size)
    pos = 0
    while pos < len(data):
        n = data[pos]
        if n == 0:
            pos = (pos // SECTOR + 1) * SECTOR
            continue
        rec = data[pos:pos + n]
        pos += n
        nlen = rec[32]
        nome = rec[33:33 + nlen]
        if nome in (b"\x00", b"\x01"):
            continue
        yield (nome.decode("latin-1").split(";")[0], u32(rec, 2), u32(rec, 10),
               bool(rec[25] & 2))


def andar(f, lba, size, prefixo, saida):
    for nome, ext, tam, eh_dir in le_dir(f, lba, size):
        caminho = prefixo + "\\" + nome
        if eh_dir:
            andar(f, ext, tam, caminho, saida)
        else:
            saida.append((caminho, ext, tam))


def copiar(f, lba, tam, destino, limite=None):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    restante = tam if limite is None else min(tam, limite)
    f.seek(lba * SECTOR)
    with open(destino, "wb") as o:
        while restante > 0:
            bloco = f.read(min(restante, 8 * 1024 * 1024))
            if not bloco:
                break
            o.write(bloco)
            restante -= len(bloco)


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__)
        sys.exit(1)
    iso = args[0]
    tudo = "--tudo" in args
    base = os.path.join(os.path.dirname(os.path.abspath(iso)), "extract")
    if "-o" in args:
        base = args[args.index("-o") + 1]

    arquivos = []
    with open(iso, "rb") as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[1:6] != b"CD001":
            sys.exit("Nao parece um ISO9660 (sem CD001 no setor 16).")
        raiz = pvd[156:190]
        andar(f, u32(raiz, 2), u32(raiz, 10), "", arquivos)
        arquivos.sort(key=lambda x: x[0].lower())

        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "mapa_lba.txt"), "w", encoding="utf-8") as m:
            m.write("caminho | LBA | bytes\n")
            for c, lba, tam in arquivos:
                m.write(f"{c} | {lba} | {tam}\n")

        for i, (c, lba, tam) in enumerate(arquivos, 1):
            rel = c.lstrip("\\").replace("\\", os.sep)
            completo = tudo or any(c.upper().startswith(p) or c.upper() == p
                                   for p in COMPLETOS)
            if completo:
                copiar(f, lba, tam, os.path.join(base, rel))
                modo = "completo"
            else:
                copiar(f, lba, tam, os.path.join(base, rel + ".head"), HEAD)
                modo = "inicio"
            print(f"[{i}/{len(arquivos)}] {modo:8} {c}")
    print(f"Pronto: {base}")


if __name__ == "__main__":
    main()

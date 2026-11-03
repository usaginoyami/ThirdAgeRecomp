#!/usr/bin/env python3
"""Lista o conteudo de um ISO9660 (disco de PS2) sem extrair nada.

Uso:  python listar_iso.py "The Third Age.iso"
Saida: lista_iso.txt (ao lado do ISO) com caminho, LBA, tamanho e os primeiros
bytes de cada arquivo (para identificar formatos). Nao precisa de bibliotecas.
Nada do jogo e copiado: so nomes, tamanhos e 16 bytes iniciais por arquivo.
"""
import os
import struct
import sys

SECTOR = 2048


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def le_dir(f, lba, size):
    f.seek(lba * SECTOR)
    data = f.read(size)
    pos = 0
    while pos < len(data):
        n = data[pos]
        if n == 0:  # padding ate o proximo setor
            pos = (pos // SECTOR + 1) * SECTOR
            continue
        rec = data[pos:pos + n]
        pos += n
        extent, dsize, flags, nlen = u32(rec, 2), u32(rec, 10), rec[25], rec[32]
        nome = rec[33:33 + nlen]
        if nome in (b"\x00", b"\x01"):
            continue
        nome = nome.decode("latin-1").split(";")[0]
        yield nome, extent, dsize, bool(flags & 2)


def andar(f, lba, size, prefixo, saida):
    for nome, ext, tam, eh_dir in le_dir(f, lba, size):
        caminho = prefixo + "\\" + nome
        if eh_dir:
            saida.append((caminho + "\\", ext, 0, b""))
            andar(f, ext, tam, caminho, saida)
        else:
            f.seek(ext * SECTOR)
            saida.append((caminho, ext, tam, f.read(16)))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    iso = sys.argv[1]
    saida = []
    with open(iso, "rb") as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[1:6] != b"CD001":
            sys.exit("Nao parece um ISO9660 (sem CD001 no setor 16).")
        raiz = pvd[156:190]
        andar(f, u32(raiz, 2), u32(raiz, 10), "", saida)
    destino = os.path.join(os.path.dirname(os.path.abspath(iso)), "lista_iso.txt")
    total = 0
    with open(destino, "w", encoding="utf-8") as o:
        o.write("caminho | LBA | bytes | primeiros 16 bytes (hex)\n")
        for caminho, lba, tam, cab in sorted(saida, key=lambda x: x[0].lower()):
            total += tam
            o.write(f"{caminho} | {lba} | {tam} | {cab.hex()}\n")
        o.write(f"\nTOTAL: {len(saida)} entradas, {total} bytes\n")
    print(f"Pronto: {destino}  ({len(saida)} entradas)")


if __name__ == "__main__":
    main()

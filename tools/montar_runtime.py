#!/usr/bin/env python3
"""Monta e compila o runtime do PS2Recomp com o codigo recompilado do Third Age (sem tocar no submodulo).

Uso (na raiz do repo):  python tools/montar_runtime.py [--so-montar] [--gerar] [--tipo Release]

Passos:
  1. (--gerar) compila ps2_recomp e recompila dados/SLUS_210.27 com config/thirdage.toml -> generated/
  2. copia thirdparty/PS2Recomp para build/stage (sem .git) e poe o codigo gerado em
     ps2xRuntime/src/runner (.cpp) e ps2xRuntime/include (.h)
  3. cmake + build do alvo ps2EntryRunner em build/runtime (Ninja se existir)
Nada do jogo e versionado: generated/, build/ e dados/ estao no .gitignore.
"""
import argparse
import os
import shutil
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SUB = os.path.join(RAIZ, "thirdparty", "PS2Recomp")
STAGE = os.path.join(RAIZ, "build", "stage")
GEN = os.path.join(RAIZ, "generated")


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def gerar(tipo):
    bd = os.path.join(RAIZ, "build", "ps2recomp")
    gen = ["-G", "Ninja"] if shutil.which("ninja") else []
    run(["cmake", "-S", SUB, "-B", bd, *gen, f"-DCMAKE_BUILD_TYPE={tipo}",
         "-DPS2X_BUILD_RUNTIME=OFF", "-DPS2X_BUILD_TEST=OFF", "-DPS2X_BUILD_STUDIO=OFF"])
    run(["cmake", "--build", bd, "--target", "ps2_recomp", "--config", tipo, "-j", str(os.cpu_count() or 2)])
    exe = None
    for raiz, _, arqs in os.walk(bd):
        for a in arqs:
            if a in ("ps2_recomp", "ps2_recomp.exe"):
                exe = os.path.join(raiz, a)
    if not exe:
        sys.exit("ps2_recomp nao encontrado apos o build")
    if os.path.isdir(GEN):
        shutil.rmtree(GEN)
    run([exe, os.path.join("config", "thirdage.toml")], cwd=RAIZ)


def montar():
    if not os.path.isdir(GEN) or not os.path.exists(os.path.join(GEN, "register_functions.cpp")):
        sys.exit("generated/ vazio: rode com --gerar (precisa de dados/SLUS_210.27)")
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    shutil.copytree(SUB, STAGE, ignore=shutil.ignore_patterns(".git", "build*", "ps2xStudio", "android", "vita"))
    runner = os.path.join(STAGE, "ps2xRuntime", "src", "runner")
    inc = os.path.join(STAGE, "ps2xRuntime", "include")
    os.makedirs(runner, exist_ok=True)
    n = 0
    for a in os.listdir(GEN):
        dest = inc if a.endswith(".h") else runner
        shutil.copy2(os.path.join(GEN, a), os.path.join(dest, a))
        n += 1
    print(f"{n} arquivos gerados copiados para {STAGE}")


def compilar(tipo):
    bd = os.path.join(RAIZ, "build", "runtime")
    gen = ["-G", "Ninja"] if shutil.which("ninja") else []
    run(["cmake", "-S", STAGE, "-B", bd, *gen, f"-DCMAKE_BUILD_TYPE={tipo}",
         "-DPS2X_BUILD_RECOMP=OFF", "-DPS2X_BUILD_ANALYZER=OFF", "-DPS2X_BUILD_TEST=OFF",
         "-DPS2X_BUILD_STUDIO=OFF", "-DPS2X_ENABLE_DEBUG_UI=OFF"])
    run(["cmake", "--build", bd, "--target", "ps2EntryRunner", "--config", tipo, "-j", str(os.cpu_count() or 2)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gerar", action="store_true", help="recompila o ELF antes (gera generated/)")
    ap.add_argument("--so-montar", action="store_true", help="so copia para build/stage, sem compilar")
    ap.add_argument("--tipo", default="Release")
    a = ap.parse_args()
    if a.gerar:
        gerar(a.tipo)
    montar()
    if not a.so_montar:
        compilar(a.tipo)


if __name__ == "__main__":
    main()

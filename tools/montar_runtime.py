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
import platform
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


def limpa_cache_se_mudou(bd):
    """Se a pasta de build foi copiada de outro lugar, o CMakeCache aponta para o caminho antigo: apaga."""
    cache = os.path.join(bd, "CMakeCache.txt")
    if not os.path.exists(cache):
        return
    atual = os.path.normcase(os.path.abspath(bd)).replace("\\", "/").lower()
    for linha in open(cache, encoding="utf-8", errors="replace"):
        if linha.startswith("CMAKE_CACHEFILE_DIR:"):
            ant = linha.split("=", 1)[1].strip().replace("\\", "/").lower()
            if ant != atual:
                print(f"Cache do CMake de outro caminho ({ant}); apagando {bd}")
                shutil.rmtree(bd)
            return


def gerar(tipo):
    bd = os.path.join(RAIZ, "build", "ps2recomp")
    gen = ["-G", "Ninja"] if shutil.which("ninja") else []
    limpa_cache_se_mudou(bd)
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


# O tradutor de VCLIP do PS2Recomp grava os bits de CLIP invertidos (-x antes de +x) e compara com w sem valor absoluto.
# O VU real usa bit0=+x, bit1=-x, bit2=+y, bit3=-y, bit4=+z, bit5=-z. O jogo testa com a mascara 0x2f (ignora +z), entao
# um z grande marcava o vertice como fora da tela (ADC=1) e nada era desenhado. O codigo gerado e corrigido aqui.
VCLIP_ERRADO = (
    b"__m128 neg_ft = _mm_xor_ps(ft, _mm_castsi128_ps(_mm_set1_epi32(0x80000000))); ",
    b"uint32_t flags = ((lt_mask & 0x1) << 0) | ((gt_mask & 0x1) << 1) | ((lt_mask & 0x2) << 1) | ((gt_mask & 0x2) << 2) | ((lt_mask & 0x4) << 2) | ((gt_mask & 0x4) << 3); ",
)
VCLIP_CERTO = (
    b"ft = _mm_andnot_ps(_mm_castsi128_ps(_mm_set1_epi32(0x80000000)), ft); __m128 neg_ft = _mm_xor_ps(ft, _mm_castsi128_ps(_mm_set1_epi32(0x80000000))); ",
    b"uint32_t flags = ((gt_mask & 0x1) << 0) | ((lt_mask & 0x1) << 1) | ((gt_mask & 0x2) << 1) | ((lt_mask & 0x2) << 2) | ((gt_mask & 0x4) << 2) | ((lt_mask & 0x4) << 3); ",
)


# vf0 e fixo em (0,0,0,1) no VU real. O jogo usa `vsub $vf0, a, b` so para atualizar as flags MAC e le com `cfc2 $vi17`, mas o
# PS2Recomp grava o resultado em vf0 (estragando todo vmax/vmul seguinte) e nunca atualiza vu0_mac_flags. A flag so tem Z e S.
VF0_ERRADO = b"ctx->vu0_vf[0] = PS2_VBLEND(ctx->vu0_vf[0], res, _mm_castsi128_ps(mask));"
VF0_CERTO = (
    b"static const uint8_t ps2xInv4[16] = {0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15}; "
    b"const int ps2xDest = _mm_movemask_ps(_mm_castsi128_ps(mask)); "
    b"const int ps2xS = _mm_movemask_ps(res) & ps2xDest; "
    b"const int ps2xZ = _mm_movemask_ps(_mm_cmpeq_ps(res, _mm_setzero_ps())) & ps2xDest; "
    b"ctx->vu0_mac_flags = static_cast<uint32_t>((ps2xInv4[ps2xS] << 4) | ps2xInv4[ps2xZ]);"
)


def corrigir_gerado():
    """Devolve os nomes dos arquivos alterados; os demais mantem a data, para o build nao recompilar tudo."""
    alterados = []
    for a in os.listdir(GEN):
        if not a.endswith(".cpp"):
            continue
        caminho = os.path.join(GEN, a)
        with open(caminho, "rb") as f:
            dados = f.read()
        if VCLIP_ERRADO[1] not in dados and VF0_ERRADO not in dados:
            continue
        for errado, certo in zip(VCLIP_ERRADO, VCLIP_CERTO):
            dados = dados.replace(errado, certo)
        dados = dados.replace(VF0_ERRADO, VF0_CERTO)
        with open(caminho, "wb") as f:
            f.write(dados)
        alterados.append(a)
    print(f"VCLIP e vf0 corrigidos em {len(alterados)} arquivos gerados")
    return alterados


def montar():
    if not os.path.isdir(GEN) or not os.path.exists(os.path.join(GEN, "register_functions.cpp")):
        sys.exit("generated/ vazio: rode com --gerar (precisa de dados/SLUS_210.27)")
    corrigir_gerado()
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    shutil.copytree(SUB, STAGE, ignore=shutil.ignore_patterns(".git", "build*", "ps2xStudio", "android", "vita"))
    pdir = os.path.join(RAIZ, "tools", "patches")
    if not os.path.isdir(pdir) or not any(f.endswith(".patch") for f in os.listdir(pdir)):
        sys.exit("ERRO: faltam os patches em tools\\patches\\ (0001-sif-sreg-mailbox.patch). Faca git pull ou copie a pasta.")
    if "sceSifGetSreg@0x0032A250" not in open(os.path.join(RAIZ, "config", "thirdage.toml")).read():
        sys.exit("ERRO: config\\thirdage.toml desatualizado (falta sceSifGetSreg@0x0032A250). Faca git pull.")
    for pf in sorted(os.listdir(pdir)):
        if pf.endswith(".patch"):
            run(["git", "apply", "--whitespace=nowarn", "--directory=build/stage", os.path.join(pdir, pf)], cwd=RAIZ)
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
    limpa_cache_se_mudou(bd)
    # o codigo gerado usa SSE4.1 (_mm_blendv_ps etc.); gcc/clang precisam do flag
    sse = ["-DCMAKE_CXX_FLAGS=-msse4.1", "-DCMAKE_C_FLAGS=-msse4.1"] \
        if platform.machine().lower() in ("amd64", "x86_64") and "cl" not in os.path.basename(os.environ.get("CXX", "")).lower() else []
    gen = ["-G", "Ninja"] if shutil.which("ninja") else []
    run(["cmake", "-S", STAGE, "-B", bd, *gen, f"-DCMAKE_BUILD_TYPE={tipo}", *sse,
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

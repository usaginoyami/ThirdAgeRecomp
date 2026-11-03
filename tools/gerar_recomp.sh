#!/usr/bin/env bash
# Compila o PS2Recomp (recompilador + analisador) e recompila o ELF do Third Age.
# Uso (na raiz do repo):  tools/gerar_recomp.sh [analisar]
#   sem argumento: usa config/thirdage.toml;  "analisar": regera o TOML com o analisador nativo.
# Requer: cmake, ninja, g++ 13+ e o ELF em dados/SLUS_210.27 (nao versionado).
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="${BUILD_DIR:-$RAIZ/build/ps2recomp}"
ELF="$RAIZ/dados/SLUS_210.27"
[ -f "$ELF" ] || { echo "Falta $ELF (extraia do disco com tools/extrair_iso.py)"; exit 1; }
[ -f "$RAIZ/thirdparty/PS2Recomp/CMakeLists.txt" ] || git -C "$RAIZ" submodule update --init thirdparty/PS2Recomp

if [ ! -x "$BUILD/ps2xRecomp/ps2_recomp" ]; then
  cmake -S "$RAIZ/thirdparty/PS2Recomp" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DPS2X_BUILD_RUNTIME=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF
  ninja -C "$BUILD" -j"$(nproc)" ps2_analyzer ps2_recomp
fi

cd "$RAIZ"
if [ "${1:-}" = "analisar" ]; then
  "$BUILD/ps2xAnalyzer/ps2_analyzer" "$ELF" config/thirdage.toml
  sed -i 's|^input = .*|input = "dados/SLUS_210.27"|; s|^output = .*|output = "generated/"|' config/thirdage.toml
fi
"$BUILD/ps2xRecomp/ps2_recomp" config/thirdage.toml
echo "Saida em $RAIZ/generated ($(ls generated | wc -l) arquivos)"

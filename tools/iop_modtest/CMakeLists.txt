cmake_minimum_required(VERSION 3.21)
project(iop_modtest LANGUAGES CXX)
# Harness proprio: carrega os IRX do disco no emulador de IOP do PS2Recomp (ps2xIOP).
# IOP_SRC: pasta do ps2xIOP (padrao: submodulo; use build/stage/ps2xIOP para a versao com os patches)
set(IOP_SRC "${CMAKE_CURRENT_SOURCE_DIR}/../../thirdparty/PS2Recomp/ps2xIOP" CACHE PATH "")
add_subdirectory(${IOP_SRC} ps2xIOP EXCLUDE_FROM_ALL)
add_executable(iop_modtest iop_modtest.cpp)
target_link_libraries(iop_modtest PRIVATE ps2_iop)

cmake_minimum_required(VERSION 3.21)
project(iop_modtest LANGUAGES CXX)
# Harness proprio: carrega os IRX do disco no emulador de IOP do PS2Recomp (ps2xIOP).
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/../../thirdparty/PS2Recomp/ps2xIOP ps2xIOP EXCLUDE_FROM_ALL)
add_executable(iop_modtest iop_modtest.cpp)
target_link_libraries(iop_modtest PRIVATE ps2_iop)

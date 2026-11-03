# Primeira recompilação — análise nativa (2026-11-02)

Rodado no sandbox (Linux, g++ 13, cmake 3.28) com o PS2Recomp do submódulo (`e563698`), `ps2_analyzer` + `ps2_recomp`, reproduzível com `tools/gerar_recomp.sh`.

## Resultado
| Item | Valor |
|---|---|
| Funções extraídas | 10.536 (10.540 arquivos `.cpp`/`.h` gerados) |
| Código C++ gerado | ~173 MB |
| Funções do SDK Sony reconhecidas (stubs) | 102 (ex.: `sceGs*`, `exit`, `__divdi3`) |
| Funções de biblioteca sem handler no runtime | 268 (a tratar) |
| Entry point | 0x110008 → `_InitSys`, depois `sub_003287E0` e `sub_001C29C8` |
| Tempo do recompilador | ~2 s |
| Erros | 0 |
| Avisos | 2.818 — todos "JR/JALR indireto não resolvido; entradas de reserva promovidas" |
| Tabelas de salto detectadas | 0 (suspeito: um jogo desse porte tem muitos `switch`) |

## Verificação
- Amostra de 40 arquivos gerados (aleatória e fixa) compilada com `g++ -std=c++20 -fsyntax-only` contra os headers do runtime do PS2Recomp: **40/40 sem erro**. Não é compilação completa, e o runtime ainda não foi construído nem linkado.
- Acessos a hardware (MMIO) detectados, entre outros: DMA (`0x1000A000`, `0x10009000`, `0x1000B400`, `0x1000D400`, `0x1000D480`, `0x1000E010/E020`).

## Limitações / próximos passos
1. A análise nativa é menos precisa em ELFs stripped. O export do **Ghidra** deve resolver as tabelas de salto (ver `docs/GHIDRA.md`).
2. Os 268 handlers ausentes e os módulos IOP precisam de HLE no runtime (CD por LBA, memory card, pad, SPU2 e `AUDIOPF`).
3. Compilar e linkar tudo (10.540 unidades) com o runtime e fazer o primeiro boot headless.
4. Região `0x347670–0x348CC0` (final do `.text`, antes do `.vutext`): vários `jr` indiretos em sequência, provavelmente despacho de funções (a conferir no Ghidra).

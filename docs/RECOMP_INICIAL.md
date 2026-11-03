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
1. Os ~3,4 mil `jr`/`jalr` indiretos (provavelmente `switch`) seguem sem resolução estática tanto no nativo quanto no export do Ghidra (ver a comparação abaixo e `docs/GHIDRA.md`); o runtime os resolve por `lookupFunction`, a validar no boot.
2. Os 268 handlers ausentes e os módulos IOP precisam de HLE no runtime (CD por LBA, memory card, pad, SPU2 e `AUDIOPF`).
3. Compilar e linkar tudo (10.540 unidades) com o runtime e fazer o primeiro boot headless.
4. Região `0x347670–0x348CC0` (final do `.text`, antes do `.vutext`): vários `jr` indiretos em sequência, provavelmente despacho de funções (a conferir no Ghidra).

## Comparação: análise nativa × export do Ghidra (2026-11-02)
Ghidra 12.1.4 + extensão ghidra-emotionengine-reloaded v2.1.38, script `ExportPS2Functions` do PS2Recomp. Configs: `config/thirdage.native.toml` (nativo) e `config/thirdage.toml` (Ghidra + stubs do SDK mesclados; `config/thirdage.ghidra.csv`).

| | Nativo | Ghidra (mesclado) |
|---|---|---|
| Funções / pontos de entrada | 10.536 | 9.207 funções + 39.138 rótulos (48.345 registros; 37.205 viram `entry_`) |
| Arquivos gerados | 10.540 | 48.348 |
| Tamanho do C++ | 173 MB | 356 MB |
| Stubs (kernel + SDK) | 102 (SDK) | 146 (44 do kernel do Ghidra + 102 do SDK do nativo, sem conflito de nome) |
| Sítios de `jr`/`jalr` indireto sem resolver (únicos) | 3.423 | 3.456 |
| Erros do recompilador | 0 | 0 |
| Amostra de 40 arquivos (`-fsyntax-only`) | 40/40 | 40/40 |

**Conclusão provisória:** a hipótese de que o Ghidra reduziria os saltos indiretos **não se confirmou**: o recompilador usa só os limites de função e os pontos de entrada do CSV, não as tabelas de salto, então os mesmos ~3,4 mil sítios continuam sem resolução estática. O que o Ghidra acrescenta são limites de função mais confiáveis e 1.861 rótulos `caseD_*` (destinos de `switch`) como pontos de entrada, em troca de dobrar o código gerado. Qual dos dois funciona melhor só se decide no boot (se os `switch` despacham certo pelo `lookupFunction` do runtime). O padrão fica no Ghidra (recomendação do README do PS2Recomp); o nativo fica como alternativa.

O Ghidra não nomeou nenhuma função do SDK Sony (`sceGs*`, `sceCd*`...): o script não usa banco de símbolos. Os 102 nomes vieram do analisador nativo, por assinatura.

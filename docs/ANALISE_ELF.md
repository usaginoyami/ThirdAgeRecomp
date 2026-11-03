# Análise do ELF — SLUS_210.27 (NTSC-U) — 2026-11-02

Fonte: `readelf`/`strings` no executável extraído do disco (não versionado, fica em `dados/`).

## Visão geral
- Boot: `BOOT2 = cdrom0:\SLUS_210.27;1`, NTSC.
- ELF32 little-endian, MIPS R5900 (flags `5900`, mips3), estático, **sem símbolos** (stripped).
- Entry point: `0x00110008`. Um único segmento LOAD em `0x00110000`, 0x2916d8 bytes no arquivo, 0x338da8 na memória.
- Tamanho do arquivo: 2.765.452 bytes.

## Seções
| Seção | Endereço | Tamanho | Nota |
|---|---|---|---|
| `.text` | 0x00110000 | 0x238d18 (~2,2 MB) | ~582 mil instruções MIPS |
| `.vutext` | 0x00348d80 | 0x10760 (~66 KB) | código/microcódigo de VU embutido |
| `.data` | 0x00359500 | 0x2ba38 | |
| `.rodata` | 0x00384f80 | 0x1c758 | |
| `.bss` | 0x003a1780 | 0xa7628 | |
| `.DVP.overlay.*` (36) | — | ~63 KB total | overlays de VU (toolchain SN/DVP) |
| `.DVP.ovlytab` / `ovlystrtab` | — | 0x1b0 / 0x559 | tabela de overlays VU |

Observação: os "overlays" aqui são **overlays de microcódigo de VU1** (ProDG/DVP), não overlays de código EE. Isso é diferente do DQ8; o código EE parece ser um único bloco.

## Bibliotecas e middleware (strings)
- **Havok** (física e `ClHavokCharacterProxy`) — com checagem de chave/avaliação (pode precisar de stub).
- **Lua 4.0** (`LuaManager`, `RegisterLuaScript`, tolua) — scripts do jogo (`.scp`).
- SDK Sony: `libpad` (2800), `libcdvd` (2800), `libmc` (2810), **`libipu`** (2800, MPEG para vídeos), libsd.
- Módulos IRX carregados: `LIBSD`, `MCMAN`, `MCSERV`, `SIO2MAN`, `SIO2D`, `USBD`, `DBCMAN`, `DS2U_D`, `AUDIOPF` e `cdrom0:\MODULES\IOPRP280.IMG`.

## Arquivos referenciados
- `Data/LoadOnce.scp`, `Data/Game/GlobScen.scp`, `Data/Game/e98c/e98c03.scp`
- `Data/Movies/%s/%s` e `data\movies\blakfmv1.ps2` (vídeos `.ps2`)
- Ícone de save: `icon.sys`, `lotrtta.ico`

## Implicações para o recomp
1. **CPU EE:** um bloco de ~2,2 MB de código sem overlays EE → recompilação direta, sem tratamento de overlay de código.
2. **VU1:** ~66 KB de `.vutext` + 36 overlays DVP. Dá para levantar os microprogramas (como o census do AC5/Gitaroo) antes de decidir interpretar ou traduzir.
3. **Vídeos:** `.ps2` = contêiner próprio (não `.PSS`) com MPEG via libipu → precisa de decoder de IPU/MPEG e de extração do formato.
4. **Física Havok e Lua 4.0:** vêm compilados dentro do ELF, então são recompilados junto; a checagem de chave do Havok pode exigir stub.
5. **IOP:** vários IRX (SIO2, USB, DBC, áudio). Só os essenciais precisam de HLE (CD, memory card, pad, SPU2).

## Próximos passos
- [ ] Abrir no Ghidra e exportar funções para o PS2Recomp
- [ ] Listar o conteúdo do ISO (4,6 GB) — ver `docs/STATUS.md`
- [ ] Census dos microprogramas VU1 (`.vutext` + overlays)

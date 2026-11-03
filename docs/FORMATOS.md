# Formatos de arquivo — The Third Age (2026-11-02)

Resultado da análise de amostras reais do disco (`tools/extrair_iso.py`). Nada do conteúdo do jogo é versionado.

## Vídeos `Data\Movies\*\*.PS2`
Contêiner simples: **cabeçalho de 0x40 bytes + fluxo MPEG-2 de vídeo puro (elementary stream)**, sem áudio embutido.

| Offset | Valor (E3C1F12) | Significado |
|---|---|---|
| 0x00 | `32 47 50 4d` | assinatura "MPG2" (little-endian) |
| 0x04 | 0x1000 | (provável) tamanho de bloco/alinhamento |
| 0x08 | 0xE6 = 230 | número de quadros |
| 0x14 | 0xFC0 | a investigar (4032) |
| 0x40 | `00 00 01 B3` | início do fluxo MPEG-2 (sequence header) |

- Vídeo: **512×448**, código de taxa de quadros 4 (≈29,97 fps), I/P/B, 16 GOPs na amostra.
- Termina com `sequence_end` (`00 00 01 B7`) seguido de um marcador (`LLIFXo`) e preenchimento com zeros até o fim do setor.
- Tamanho do arquivo múltiplo de 2048.
- **Não encontrei áudio dentro do arquivo**; o áudio das cenas deve vir de seções `xs_aud_*` dos `.SAS`/`.SCP` (a confirmar).
- Todos os 120 vídeos têm a mesma assinatura.

**Implicação:** o decodificador pode ser qualquer decodificador MPEG-2 de software (libmpeg2, FFmpeg, pl_mpeg) alimentado pelo `sceMpeg`/IPU HLE; não é preciso desmultiplexar PSS.

## Scripts `.SCP` e dados `.SAS` (`Data\Game\*`)
- Dois tipos de `.SCP`:
  - `GLOBSCEN.SCP`, `LOADONCE.SCP`: assinatura `LRTC` ("CTRL"), blocos `SYNC`, `SHOC`, `PADD`; `LOADONCE` contém `audio:ENG` e `text:ENG` (seleção de idioma).
  - Os das fases (`E01C01.SCP`...): assinatura `COTS` ("STOC"), um índice de **seções nomeadas** com sufixo de região e idioma: `initial_load_ntsc_eng`, `zone_e98c02_zone1_ntsc_eng`, `xsection_01_ntsc_eng`, e várias `xs_aud_game_*_ntsc_eng` (áudio).
- Este disco (NTSC-U) só tem o idioma `eng`.
- `.SAS` são os dados que as seções do `.SCP` referenciam (cabeçalhos diferentes: `0c 02`, `0b 02`, `13 02`); formato proprietário da EA, lido pelo próprio jogo.
- **Implicação:** o recomp não precisa decodificar `.SCP`/`.SAS`; basta o CD HLE entregar os bytes corretos por LBA/offset, com leitura de arquivos grandes sem travar.

## Módulos IOP (`Modules\`)
- `IOPRP280.IMG`: imagem padrão da Sony ("RESET", ROMDIR com 19 entradas: SYSMEM, LOADCORE, SIFCMD, SIFMAN, THREADMAN, IOMAN, MODLOAD, FILEIO, **CDVDMAN, CDVDFSV**, LOADFILE, TIMEMANI, ROMDRV, EESYNC, SYSCLIB, STDIO). É o SDK 2.8: o jogo faz `sceSifRebootIop` com ela. No HLE basta aceitar o reboot.
- IRX do jogo (MIPS R3000 do IOP): `LIBSD` (áudio, v2710), `MCMAN`/`MCSERV` (memory card), `SIO2MAN`/`SIO2D` (pad), `DS2U_D`, `DBCMAN` (adaptador de controle), `AUDIOPF` (áudio do jogo, usa libsd; 98 KB, o maior).
- `AUDIOPF.IRX` é o único módulo específico do jogo com lógica própria: ver se o áudio precisa de HLE próprio ou se dá para emular o IOP só nos serviços usados.

## Próximas investigações
- [ ] Onde está o áudio dos vídeos (campo 0x14 = 0xFC0? seções `xs_aud_*`?).
- [ ] Estrutura do índice `COTS` (offsets/tamanhos das seções) para validar o streaming.
- [ ] Interface RPC do `AUDIOPF.IRX`.

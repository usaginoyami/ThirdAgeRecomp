# Status (2026-11-02)

## Feito
- Estrutura do repositório e push no GitHub.
- Fase 0 concluída em grande parte:
  - ELF `SLUS_210.27` — `docs/ANALISE_ELF.md`
  - Disco (156 arquivos, 4,27 GB) — `docs/ISO_LAYOUT.md`
  - Formatos (vídeo MPEG-2 puro 512x448, índices SCP/SAS, IOPRP280) — `docs/FORMATOS.md`
- Ferramentas: `tools/listar_iso.py`, `tools/extrair_iso.py` (+ `.bat`).

## Pendente
- Ghidra: exportar funções para o PS2Recomp.
- Census de VU1 (`.vutext` + 36 overlays DVP).
- Primeiro boot headless: HLE de CD (lendo o ISO por LBA), kernel EE e IOP.
- Áudio: descobrir onde fica o áudio dos vídeos e o RPC do `AUDIOPF.IRX`.

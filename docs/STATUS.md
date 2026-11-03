# Status (2026-11-02)

## Feito
- Estrutura do repositório e push no GitHub.
- Fase 0: ELF `SLUS_210.27` analisado — `docs/ANALISE_ELF.md`.
- Fase 0: disco listado (156 arquivos, 4,27 GB) — `docs/ISO_LAYOUT.md`.
- Ferramentas: `tools/listar_iso.py`, `tools/extrair_iso.py` (+ `.bat`).

## Pendente
- Rodar `Extrair_ISO.bat` no PC (extração seletiva, ~150 MB) e analisar o contêiner `.PS2` (2GPM), `IOPRP280.IMG` e os cabeçalhos `.SCP`/`.SAS`.
- Ghidra: exportar funções para o PS2Recomp.
- Census de VU1 (`.vutext` + 36 overlays DVP).
- Decisão: runtime de CD lendo o ISO direto por LBA.

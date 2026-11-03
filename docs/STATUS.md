# Status (2026-11-02)

## Feito
- Estrutura do repositório e push no GitHub.
- Fase 0: ELF (`docs/ANALISE_ELF.md`), disco (`docs/ISO_LAYOUT.md`), formatos (`docs/FORMATOS.md`).
- Fase 1 (parcial): PS2Recomp compilado no sandbox; análise nativa + recompilação do ELF inteiro: 10.536 funções, 0 erros, 2.818 avisos de `jr` indireto (`docs/RECOMP_INICIAL.md`). Amostra de 40 arquivos gerados compila (`-fsyntax-only`).
- Census de VU1 (estático): 8 microprogramas carregados por 36 pacotes MPG (7.908 pares); os 36 overlays DVP são só descrições. `docs/VU1_CENSUS.md`, `tools/vu1_census.py`.
- IOP: os 8 IRX do disco carregam e iniciam no ps2xIOP (`docs/IOP_MODULOS.md`, `tools/iop_modtest`). As "268 funções sem handler" eram leitura errada: são código recompilado normal.
- Ferramentas: `tools/listar_iso.py`, `tools/extrair_iso.py`, `tools/gerar_recomp.sh`, `tools/vu1_census.py`.
- Ghidra 12.1.4 rodado pelo usuário no ELF (9.207 funções); export em `config/thirdage.ghidra.*` e recompilação com ele: 48.348 arquivos, 356 MB, 0 erros, amostra de 40 compila. Comparação em `docs/RECOMP_INICIAL.md`.

## Pendente
- ~3,4 mil `jr` indiretos continuam sem resolução estática (nativo e Ghidra empatam); decidir no boot qual config usar.
- Compilar e linkar o código gerado com o runtime (ps2xRuntime), que ainda não foi construído.
- HLE: CD lendo o ISO por LBA, `sceSifLoadModule`/reboot do IOP (`IOPRP280.IMG`), RPC de `AUDIOPF`/`DS2U_D`, áudio e filmes.

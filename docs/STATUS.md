# Status (2026-11-02)

## Feito
- Estrutura do repositório e push no GitHub.
- Fase 0: ELF (`docs/ANALISE_ELF.md`), disco (`docs/ISO_LAYOUT.md`), formatos (`docs/FORMATOS.md`).
- Fase 1 (parcial): PS2Recomp compilado no sandbox; análise nativa + recompilação do ELF inteiro: 10.536 funções, 0 erros, 2.818 avisos de `jr` indireto (`docs/RECOMP_INICIAL.md`). Amostra de 40 arquivos gerados compila (`-fsyntax-only`).
- Ferramentas: `tools/listar_iso.py`, `tools/extrair_iso.py`, `tools/gerar_recomp.sh`.
- Guia e script do Ghidra prontos para o PC (`docs/GHIDRA.md`, pasta `ghidra\` ao lado do ISO).

## Pendente
- Usuário: rodar o Ghidra e exportar `config/thirdage.ghidra.toml` + `.csv` (resolve as tabelas de salto).
- Compilar e linkar o código gerado com o runtime (ps2xRuntime), que ainda não foi construído.
- Census de VU1 (`.vutext` + 36 overlays DVP).
- HLE: CD lendo o ISO por LBA, 268 funções de biblioteca sem handler, módulos IOP, áudio (`AUDIOPF.IRX`).

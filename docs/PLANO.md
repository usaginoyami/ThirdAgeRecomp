# Plano — ThirdAgeRecomp

## Fase 0 — Análise do disco
- [ ] Extrair SYSTEM.CNF, ELF principal (SLUS) e módulos IRX
- [ ] Listar arquivos do disco (formato dos pacotes da EA, vídeos PSS/.PS2, áudio)
- [ ] Abrir o ELF no Ghidra: tamanho, overlays, SDK usado
- [ ] Levantar microcódigos de VU1 em uso

## Fase 1 — Recompilação
- [ ] Exportar funções do Ghidra (TOML/CSV) para o PS2Recomp
- [ ] Gerar o código C++ e compilar o runner
- [ ] Nomear funções do SDK (config/symbols/)

## Fase 2 — Boot headless
- [ ] HLE de kernel EE, IOP, SIF RPC, CD, pad, memory card
- [ ] Chegar ao menu sem gráficos (logs)
- [ ] Stubs e overrides em src/runtime/

## Fase 3 — Gráficos
- [ ] GS via GSdx em processo separado
- [ ] VU1 (interpretador primeiro, depois tradução se precisar)
- [ ] Texturas e cenas 3D corretas

## Fase 4 — Mídia
- [ ] Vídeos (MPEG-2/IPU)
- [x] Áudio SPU2 e músicas (patch 0037; ainda sem reverb, PMON e ruído)

## Fase 5 — Pacote
- [ ] Kit de um clique (extrair, recompilar, compilar, rodar)
- [ ] Build real no Windows, teste de janela/áudio/controle
- [ ] Licenças (GPL do GSdx isolado no processo separado)

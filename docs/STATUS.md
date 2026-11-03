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
- Build do runtime: `tools/montar_runtime.py` (+ `Montar_Runtime.bat`) recompila o ELF, monta `build/stage` (cópia do PS2Recomp + código gerado) e compila `ps2EntryRunner`. Etapa de montagem validada no sandbox; o build completo é para o PC Windows (sandbox: 2 núcleos, sem libs X11 do raylib).
- Primeiro boot (PC, 2026-11-03): ELF carrega, 8 IRX carregam na ordem do jogo (SIO2MAN, DBCMAN, SIO2D, DS2U_D, MCMAN, MCSERV, LIBSD, AUDIOPF), depois o EE fica em laço em `0x226d60` esperando `sceSifGetSreg(0x1F/0x1E)` (função do jogo em 0x32A250). Causa: o runtime não tinha o mailbox "sreg" da SIF (comando de sistema 0x80000001) nos dois sentidos; `sceSifSendCmd` do EE era no-op e o `sifcmd` do IOP devolvia 0. Correção em `tools/patches/0001-sif-sreg-mailbox.patch` (aplicado na montagem) + stub `sceSifGetSreg@0x0032A250` em `config/thirdage.toml`.
- Boot 2 (patch 0001 ativo): `AUDIOPF` registra seus comandos SIF, mas o início dele falhava (`start=1`): o heap do IOP (0x120000–0x1F0000, ~850 KB) era menor que o buffer de 786 KB que o módulo pede + a pilha da thread (CreateThread → -400, sem memória). `tools/patches/0002-iop-heap-sifinit-trace.patch`: heap do IOP passa a começar em 0x80000, `sceSifCheckInit` já retorna "iniciado" após o reset (a imagem base do IOP já tem SIFMAN/SIFCMD), e traço opcional de imports com `PS2X_IOP_TRACE_IMPORTS=1`. No harness, `AUDIOPF` agora inicia (start=0), cria 12 threads e envia SET_SREG 0x1E/0x1F ao EE.
- Boot 3: handshake SIF passou; o jogo iniciou o GS (`sceGsSyncVCallback`) e travou em `JALR 0x19872c → 0x3350e0` (`guest-branch:missing-target`): `0x3350e0` é um método virtual vazio (`jr $ra; nop`) que o Ghidra não listou (5.035 trechos de `.text`, ~92 KB, ficaram sem função). `tools/preencher_gaps.py` acrescenta 1.770 funções ao CSV (`config/thirdage.ghidra.csv`, original em `*.orig.csv`); recompilação: 49.645 arquivos, 0 erros.
- Boot 4: 2º `missing-target`: `0x221928` (entrada de vtable) fica no meio de `FUN_00221920`, que o Ghidra juntou com outros métodos. `tools/preencher_gaps.py` agora também cria `entry_` para alvos de chamada indireta (ponteiros em dados e constantes `lui+addiu/ori` no código): +306 entradas (CSV: 50.421 registros; recompilação: 49.951 arquivos, 0 erros).

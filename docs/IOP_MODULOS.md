# Módulos IOP do jogo sob o ps2xIOP (2026-11-02)

Harness próprio: `tools/iop_modtest/` (host mínimo de `IopHost`; mapeia `cdrom0:\MODULES\X.IRX` para a pasta extraída, sem diferenciar maiúsculas). Build:

    cmake -S tools/iop_modtest -B build/iopmod -G Ninja && cmake --build build/iopmod
    build/iopmod/iop_modtest <pasta do disco> [MODULO.IRX ...] [-v]

## Resultado
Os 8 IRX de `MODULES\` carregam e iniciam no emulador de IOP (R3000A rodando o IRX original), sem falha de carga e sem import desconhecido, na ordem:
`SIO2MAN, SIO2D, DBCMAN, DS2U_D, MCMAN, MCSERV, LIBSD, AUDIOPF` (~139 mil instruções, 8 threads de IOP).

| Módulo | Resultado |
|---|---|
| SIO2MAN, SIO2D, DBCMAN, DS2U_D, LIBSD | carregam, start 0 |
| MCMAN, MCSERV | carregam, start 2 (módulo removível); MCSERV com serviço HLE |
| AUDIOPF | carrega, start 1 (sem residente); sem servidor RPC registrado ainda |
| DBCMAN / LIBSD | serviços HLE do ps2xIOP ativos |

- **Ordem importa:** `DS2U_D` importa `dbcman`; carregado antes do `DBCMAN` gera `unhandled import dbcman:4`. O jogo deve carregá-los nessa ordem (confirmar no boot pelo log de `_sceSifLoadModule`).
- Falta ainda: registro RPC de `AUDIOPF` e `DS2U_D` (só aparecem após `sceSifBindRpc` do EE), e o `IOPRP280.IMG` (imagem de reset da Sony), que o `sceSifRebootIop` do jogo carrega.
- Não testado aqui: `USBD`/módulos da BIOS (vêm do ROM, não do disco).

## As "268 funções sem handler" (correção)
Eram uma leitura errada: são as `entry_points` do analisador, isto é, funções do jogo **sem handler no runtime, que o PS2Recomp recompila normalmente** a partir do código original. Composição (288 entradas): 165 libc/libm/runtime, 92 helpers de double por software (Metrowerks `dp*`), 31 `sce*`:
`scePad2*` ×13, `sceDbc*` ×8, `sceVib*` ×2, `_sceFs*` ×4, `sceMc2Sync`, `_sceCd_Poff_Intr`, `sceSifExecNotifyHandler`.
Nenhuma está no `ps2_call_list.h`; rodam como código recompilado e conversam com o IOP via SIF/RPC, então dependem do IOP (DBCMAN/PADMAN) e não de handlers novos. O trabalho real de HLE é CD por LBA, `sceSifLoadModule`/reboot do IOP e áudio.

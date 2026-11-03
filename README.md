# ThirdAgeRecomp
<img width="1448" height="1086" alt="Duck-ai-image-2026-11-03-13-08" src="https://github.com/user-attachments/assets/b6ea5b49-d853-4805-9e8c-5fd71ddbba6d" />

Port nativo de PC de **The Lord of the Rings: The Third Age** (PS2, 2004, EA) por recompilação estática, baseado no [PS2Recomp](https://github.com/ran-j/PS2Recomp).

> Em fase de planejamento. Ainda não roda nada.

Este repositório contém **só a ferramenta, configs e runtime**. Nada do jogo (disco, ELF, vídeos, áudio) é incluído; é preciso ter a sua própria cópia.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `thirdparty/PS2Recomp/` | Submódulo: recompilador + runtime base (ran-j) |
| `config/` | TOML do recompilador e símbolos nomeados |
| `src/runtime/` | Ponto de entrada, HLE e overrides específicos do Third Age |
| `src/gs/` | Integração com o renderizador de GS |
| `tools/` | Scripts de extração do disco e utilitários |
| `kit/` | Pacote de um clique (jogar.py, Jogar.bat/.sh) |
| `docs/` | Plano e status |

## Decisões

- **Base:** PS2Recomp como submódulo (correções genéricas voltam ao upstream).
- **GS:** GS do PCSX2 (GSdx) em processo separado no início; renderizador próprio depois.
- **Desenvolvimento:** Linux/sandbox headless, teste final no Windows.

Veja `docs/PLANO.md` e `docs/STATUS.md`.

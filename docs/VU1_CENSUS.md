# Census de VU1 — The Third Age (2026-11-02)

Feito com `tools/vu1_census.py` (ferramenta própria, estática) sobre `SLUS_210.27`. Os dados por programa estão em `docs/vu1_census.json` (só endereços e contagens, nenhum código do jogo).

## Como o microcódigo está guardado
- `.vutext` (0x348d80, 67.424 bytes) não é código puro: é uma sequência de **pacotes VIF**. Cada comando **MPG** (cmd 0x4A: NUM pares de 64 bits + endereço de carga) copia um pedaço de microcódigo para a memória do VU1.
- As 36 seções `.DVP.overlay.*` **vêm zeradas** no ELF; são só descrições dos pedaços. **Conferência: 36 de 36 casam com um pacote MPG** (mesmo endereço VU e mesmo tamanho). Um "overlay" nada mais é que um MPG.
- O código de VU1 é carregado em páginas de 256 pares (2 KB), e cada programa tem de 1 a 8 páginas; o maior ocupa até 0x3E78 dos 16 KB da memória de microprograma.

## Os 8 microprogramas
| # | Pedaços (endereço VU : pares) | Pares | Fim na mem. VU | E-bit | XGKICK | JR/JALR | DIV | Desvios (cond.+B/BAL) |
|---|---|---|---|---|---|---|---|---|
| P0 | 0xA80:166 | 166 | 0x0FB0 | 10 | 0 | 0 | 0 | 1 |
| P1 | 0x0, 0x800, …, 0x3000 (256 cada) + 0x3800:207 | 1.999 | 0x3E78 | 18 | 15 | 6 | 36 | 218 |
| P2 | 0x0…0x2800 (256 cada) + 0x3000:146 | 1.682 | 0x3490 | 10 | 11 | 6 | 27 | 204 |
| P3 | 0x0, 0x800, 0x1000 (256 cada) + 0x1800:71 | 839 | 0x1A38 | 9 | 5 | 0 | 8 | 42 |
| P4 | 0x0…0x2000 (256 cada) + 0x2800:7 | 1.287 | 0x2838 | 9 | 10 | 21 | 21 | 127 |
| P5 | 0x0…0x1800 (256 cada) + 0x2000:17 | 1.041 | 0x2088 | 8 | 9 | 11 | 16 | 112 |
| P6 | 0x0, 0x800 (256 cada) + 0x1000:52 | 564 | 0x11A0 | 4 | 4 | 5 | 24 | 72 |
| P7 | 0x0:256 + 0x800:74 | 330 | 0x0A50 | 20 | 0 | 0 | 2 | 7 |

Total: 7.908 pares de código (os 520 pares restantes do `.vutext` são tags DMA e VIFcodes).

Totais de instruções (classificação por campo, não é um disassembly completo): load 1.181, store 668, desvio condicional 597, B/BAL 186, flags (`FC*`/`FS*`/`FM*`) 300, DIV 134, XGKICK 54, JR/JALR 49, XTOP 31, WAITQ 26, EFU 7 (`ERCPR`/`ESIN`… etc.), RSQRT 3, SQRT 1, MFP 9, RGET 7, RINIT 6, RNEXT 3. Pares com bit E: 88.

## O que isso significa para o port
1. **Não é um microprograma único**: são 8, cada um preenchido por MPG em páginas. É bem diferente do Gitaroo/AC5 (um programa, ou poucos), então a abordagem "lift de um programa" vira "lift de 8" ou interpretar.
2. **P0 e P7 não têm XGKICK**: são rotinas de cálculo (com `RSQRT`/`SQRT`, 20 E-bits no P7). Os outros seis são programas de desenho (54 XGKICK no total).
3. **49 `JR`/`JALR`** nos programas P1, P2, P4, P5 e P6: saltos indiretos que a análise estática não resolve sozinha; precisam de census dinâmico (alvos de JR em execução) para lift.
4. Os programas **reescrevem a mesma região** (todos usam o endereço 0), então só um deles está residente por vez; o jogo troca de programa a cada MPG. O runtime tem de acompanhar o conteúdo da memória de microprograma (como o `PS2X_VU1_VERIFY` do Gitaroo), não assumir um único programa.
5. Os 8 pedaços do endereço 0 são todos **distintos** (não existe um "prelúdio" compartilhado).

## Limites desta análise
- É estática: mostra o que o jogo **carrega**, não o que **executa** nem os pontos de entrada (`MSCAL`) usados. Isso vem do census dinâmico (precisa do runtime rodando) ou de uma varredura das chamadas na EE.
- A contagem de instruções vem de campos de bits conferidos contra o disassembler open source do Gitaroo Man Native (MIT); não gerei listagem de disassembly.
- Qual programa o jogo usa em cada cena (personagem, cenário, efeitos) ainda é desconhecido.

## Census dinâmico (2026-11-06)
Com `PS2X_VU1_CENSO=1` (patch 0033), o runtime conta, por versão do código do VU1 (hash dos 16 KB), os pares executados, as entradas e os desvios tomados. Ele grava `ps2x_vu1_censo.txt` e uma cópia de cada versão (`ps2x_vu1_codigo_<hash>.bin`) no diretório da rodada, nunca no repositório. O resumo sai com `tools/vu1_censo_dinamico.py <pasta>`.

Rodada de 290 s (título, Eregion, filme e cena do jogo), com 408 milhões de pares em 7 versões:

| Versão (hash) | Pares | Entradas principais | Blocos executados | 12 blocos mais quentes |
|---|---|---|---|---|
| `08a167d6…` | 34,3% | `4d0`, `2a8`, `460`, `268` | 82 | 94,2% |
| `1a871f8c…` | 24,4% | `1ef8`, `1e68` | 87 | 93,5% |
| `72b82386…` | 21,0% | `188`, `0`, `1ea8`, `1968`, `1b80` | 101 | 83,4% |
| `61ad6251…` | 14,6% | `378`, `10`, `190`, `1f8` | 59 | 81,3% |
| `697da831…` | 3,6% | `678`, `620` | 27 | — |

O que isso mostra:
- **Os laços quentes são minúsculos:** blocos de 1 a 9 pares, ligados por desvios condicionais. Um exemplo: `630-668` (8 pares) entra 5,5 milhões de vezes na rodada. É o processamento por vértice, com testes de recorte.
- **Os `JR`/`JALR` executados têm poucos alvos** (1 a 9 por origem), todos registrados no census. Por exemplo, `de0` tem 9 alvos e `1c00` tem 4.
- **O tempo exato é semântico:** nos laços quentes, ~14% dos pares leem as flags de recorte (`FCOR`/`FCAND`) e ~5-6% são `DIV`, mas `WAITQ` quase não aparece (0,07%). O código está em software pipelining: usa o Q anterior enquanto o próximo `DIV` corre e conta com os 4 ciclos de atraso das flags do `CLIP`. Uma tradução com tempo aproximado mudaria resultados.
- Como os blocos são curtos, há valores em voo atravessando as fronteiras. Calcular as paradas só dentro do bloco, supondo o pipeline vazio na entrada, não é exato.

## Próximos passos sugeridos
- Primeiro, interpretar o VU1 no runtime (o PS2Recomp já tem interpretador) e só depois liftar os programas mais quentes, guiado por census dinâmico.
- Varrer a EE em busca de `MSCAL`/`MSCNT` (ids de entrada) e dos pacotes DMA que chamam cada MPG, para ligar programa → uso.

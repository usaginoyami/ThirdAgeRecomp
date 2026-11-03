# Layout do disco — The Third Age (SLUS-21027, NTSC-U) — 2026-11-02

Fonte: `tools/listar_iso.py` sobre o ISO de 4.595.777.536 bytes (lista completa em `dados/lista_iso.txt`, não versionada).

## Resumo
- 156 arquivos, ~4,27 GB. Último setor usado: LBA 2.233.782 (disco de camada única).
- `SYSTEM.CNF` em LBA 150000 e `SLUS_210.27` em LBA 150001; `MODULES\` em 151352+ (junto ao ELF); `DATA\` espalhado do LBA 263 em diante.

| Tipo | Qtde | Tamanho | Função provável |
|---|---|---|---|
| `.PS2` (`Data\Movies\*`) | 120 | 1,87 GB | vídeos (FMV) — cabeçalho `32 47 50 4d` = "2GPM"; mesma assinatura em todos |
| `.SAS` (`Data\Game\*`) | 12 | 1,55 GB | dados de fase transmitidos do disco (streaming); `GLOBSCEN.SAS` tem 756 MB |
| `.SCP` (`Data\Game\*`) | 13 | 837 MB | scripts/dados de cena; assinatura `43 4f 54 53` ("COTS"); `GLOBSCEN.SCP` e `LOADONCE.SCP` têm outra, `4c 52 54 43` |
| `.IRX` + `IOPRP280.IMG` | 9 | 0,6 MB | módulos IOP |
| ELF + CNF | 2 | 2,8 MB | executável e boot |

Todos os arquivos grandes têm tamanho múltiplo de 2048 e são lidos por setor.

## Organização do conteúdo
- Fases: `E01C`, `E02C`, `E03C`, `E98C` (cada uma com pares `.SAS` + `.SCP` por área, ex.: `E01C01`).
- Vídeos agrupados por capítulo: `E1C1F`, `E1C2F`, `E1C3F`, `E2C1F`...`E2C5F`, `E3C1F`...`E3C3F`, mais `ATTRL`, `E1C1I` e `LOGO`.
- Maior vídeo: `E1C1F01.PS2` (89,8 MB); menor: `E3C1F12.PS2` (2,5 MB).

## Implicações para o runtime
1. **Ler o ISO direto, por LBA.** O jogo usa `sceCdSearchFile`/`sceCdRead` e faz streaming de arquivos de centenas de MB. O runtime de CD deve abrir o `.iso` (como o AC5 com `--disc`) e honrar LBAs reais; uma pasta extraída exigiria LBAs sintéticos.
2. **Streaming pesado:** `GLOBSCEN.SAS` (756 MB) e os `.SAS` por fase precisam de leitura em segundo plano sem travar o loop do jogo.
3. **Vídeos `.PS2` (MPG2/"2GPM"):** formato próprio com cabeçalho de 0x1000 bytes (campo 0x04 = 0x1000) e MPEG-2 dentro; é preciso entender o contêiner e ligar o decoder de IPU.
4. **Módulos IOP** são pequenos (<100 KB cada); `IOPRP280.IMG` é o pacote padrão do Sony (RESET) — o HLE só precisa dos serviços usados.
5. **Formatos `SCP`/`SAS`** são do motor da EA; provavelmente só o jogo os interpreta, então o recomp não precisa decodificá-los, só entregar os bytes pelo CD.

## A investigar
- Estrutura do cabeçalho `.PS2` (0x1000 bytes) e como achar os pacotes MPEG-2.
- Se há áudio dentro dos `.PS2` ou em canal separado (SPU2/ADPCM).

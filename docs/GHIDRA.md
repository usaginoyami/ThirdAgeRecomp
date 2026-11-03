# Ghidra → PS2Recomp (guia para o PC do usuário)

Objetivo: trocar a lista de funções do analisador nativo por uma exportada do Ghidra, que resolve melhor tabelas de salto (`switch`) e limites de função em ELFs stripped. O Ghidra não roda no sandbox (download de release bloqueado); este passo é feito no Windows.

## O que precisa
- Ghidra (a versão que você já usa).
- Extensão **ghidra-emotionengine-reloaded** (chaoticgd): suporte a PS2. Baixar da página de *releases* do repositório a versão **que combina com a sua versão do Ghidra**.
- O ELF: `SLUS_210.27` (já está na pasta do projeto).
- O script `ExportPS2Functions.java` (vem no PS2Recomp, em `ps2xRecomp/tools/ghidra/`; uma cópia foi colocada em `ghidra\` ao lado do ISO).

## Passo a passo
1. **Instalar a extensão:** no Ghidra, `File → Install Extensions → +`, escolher o `.zip` da extensão e reiniciar.
2. **Importar o ELF:** crie um projeto, `File → Import File…` e escolha `SLUS_210.27`. Em *Language*, selecione o processador do Emotion Engine: **`r5900:LE:32:default`** (MIPS-R5900).
3. **Analisar:** abra o arquivo e aceite *Analyze* com os analisadores padrão. Espere terminar (o ELF tem ~580 mil instruções).
4. **Rodar o script:** `Window → Script Manager`, no ícone de pastas (*Manage Script Directories*) adicione a pasta `ghidra\` e rode **ExportPS2Functions** (categoria *PS2Recomp*).
5. **Salvar:** o script abre duas janelas de arquivo. Salve o **TOML** como `config\thirdage.ghidra.toml` e o **CSV** como `config\thirdage.ghidra.csv`.
6. Me avise: eu comparo com a análise nativa, ajusto os caminhos (`input = "dados/SLUS_210.27"`) e recompilo.

## Por que vale
A análise nativa deixou **2.818 saltos indiretos (`jr`/`jalr`) sem resolver** e **0 tabelas de salto** detectadas; o recompilador contorna promovendo entradas de reserva, mas o Ghidra deve achar as tabelas e deixar o código gerado mais correto e menor. Detalhes em `docs/RECOMP_INICIAL.md`.

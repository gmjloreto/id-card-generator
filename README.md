# Gerador de Crachas

Ferramenta visual para gerar crachas personalizados em massa a partir de uma planilha Excel. Interface grafica com PySide6 para mapeamento visual de coordenadas e geracao automatica.

## Requisitos

- Python 3.10+
- Windows, macOS ou Linux

## Instalacao

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Estrutura

```
id-card-generator/
├── gerar_crachas.py    # Ferramenta visual (interface grafica)
├── word_crachas.py     # Folha de impressao dos crachas (PDF + Word)
├── modelo.png          # Template do cracha
├── fonte.ttf           # Fonte TrueType
├── nomes.xlsx          # Planilha com nome e equipe
├── requirements.txt    # Dependencias
├── saida/              # Crachas gerados (criada automaticamente)
└── README.md
```

## Como Usar

```bash
source .venv/bin/activate
python gerar_crachas.py
```

### Passo a passo

1. **Carregar Modelo** - Selecione a imagem do template (`modelo.png`)
2. **Selecionar Planilha** - Selecione o arquivo `.xlsx` com os dados
3. **Selecionar Fonte** - Selecione o arquivo `.ttf`
4. **Mapear Nome** - Desenhe um retangulo sobre a area do nome no template
5. **Mapear Equipe** - Desenhe um retangulo sobre a area da equipe
6. **Gerar Crachas** - Clique no botao verde

### Atalhos

| Tecla | Acao |
|-------|------|
| `Ctrl+O` | Abrir imagem |
| `Ctrl+C` | Copiar coordenadas |
| `1` | Modo Nome |
| `2` | Modo Equipe |

## Validacao da Planilha

Ao selecionar a planilha, a ferramenta valida automaticamente:

- Nomes vazios
- Equipes vazias
- Nomes duplicados
- Nomes que podem conter equipe misturada

## Folha de impressao

```bash
python word_crachas.py
```

Le todas as fotos de `saida/` e monta a folha A4 para imprimir. Voce digita a
largura e a altura do cracha em mm (o tamanho final impresso), o espaco entre
eles e a margem da folha. A foto entra inteira na caixa, sem esticar e sem
cortar: o que sobra da caixa vira borda branca.

Dois arquivos saem:

- `saida/crachas.pdf` - 300 dpi, uma folha por pagina, pronto para imprimir
- `saida/crachas.docx` - um cracha por celula, editavel (o Google Docs ignora
  altura exata de linha e pode paginar diferente: para imprimir, use o PDF)

O encaixe e uma conta fechada, sem misturar orientacoes na mesma folha:

```
colunas = (190 + 2) // (54 + 2) = 3        linhas = (277 + 2) // (86 + 2) = 3
por folha = 9                              76 crachas -> 9 folhas
```

A opcao "Deitar os crachas se couber mais folha" compara a grade em pe com a
grade deitada e usa a deitada so quando ela economiza folha (empate fica em
pe). Com 65x45 mm: 10 por folha em pe contra 16 deitado, 8 folhas contra 5.

```bash
python word_crachas.py --teste   # confere layout, contagem e arquivos
```

## Funcionalidades

- **Mapeamento visual** - Selecione as coordenadas arrastando na imagem
- **Exportacao de coordenadas** - Copia no formato `BOX_NOME = (x1, y1, x2, y2)`
- **Geracao em massa** - Gera todos os crachas de uma vez
- **Tamanho de fonte adaptativo** - Ajusta automaticamente para caber no retangulo
- **Tema escuro** - Interface moderna com dark mode
- **Validacao** - Verifica a planilha antes de gerar

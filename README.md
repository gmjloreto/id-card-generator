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

## Funcionalidades

- **Mapeamento visual** - Selecione as coordenadas arrastando na imagem
- **Exportacao de coordenadas** - Copia no formato `BOX_NOME = (x1, y1, x2, y2)`
- **Geracao em massa** - Gera todos os crachas de uma vez
- **Tamanho de fonte adaptativo** - Ajusta automaticamente para caber no retangulo
- **Tema escuro** - Interface moderna com dark mode
- **Validacao** - Verifica a planilha antes de gerar

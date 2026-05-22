# 🎫 Gerador Automático de Crachás

Script Python para gerar crachás personalizados em massa a partir de uma planilha Excel. O script ajusta automaticamente o tamanho da fonte para garantir que todos os nomes caibam perfeitamente na área designada, mantendo a padronização visual.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Pillow](https://img.shields.io/badge/pillow-required-green.svg)
![Pandas](https://img.shields.io/badge/pandas-required-green.svg)

---

## 📋 Requisitos

- **Python 3.7 ou superior**
- Sistema operacional: Windows, macOS ou Linux

---

## 🔧 Instalação

### 1. Instalar Python

Se ainda não tem Python instalado:

- **Windows**: Baixe em [python.org](https://www.python.org/downloads/)
- **macOS**: `brew install python3` ou baixe em [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt install python3 python3-pip`

### 2. Instalar as bibliotecas necessárias

Abra o terminal/prompt de comando e execute:

```bash
pip install pillow pandas openpyxl
```

**Ou**, se estiver usando Python 3 especificamente:

```bash
pip3 install pillow pandas openpyxl
```

---

## 📁 Estrutura de Arquivos

Organize seus arquivos conforme a estrutura abaixo para que o script funcione corretamente:

```text
projeto-crachas/
├── gerar.py                # O script Python principal
├── modelo.png              # Imagem base do crachá (fundo)
├── fonte.ttf               # Arquivo da fonte TrueType
├── nomes.xlsx              # Planilha Excel com os dados
└── saida/                  # Pasta criada automaticamente com os resultados
    ├── NOME1.png
    ├── NOME2.png
    └── ...
```

---

## 📝 Preparando os Arquivos

### 1. **modelo.png** - Imagem Base

- Recomenda-se o uso de áreas brancas ou sólidas onde o texto será inserido.
- Dimensões sugeridas: **681 × 1021 pixels**.
- Formato: PNG (suporta transparência).

### 2. **fonte.ttf** - Arquivo da Fonte

- Utilize qualquer fonte **TrueType (.ttf)**.
- Renomeie o arquivo para `fonte.ttf` ou altere a variável `FONTE` no script.

### 3. **nomes.xlsx** - Planilha Excel

Crie uma planilha com **2 colunas** (Nome e Equipe):

| Nome               | Equipe        |
|--------------------|---------------|
| João Silva         | Louvor        |
| Maria Santos       | Intercessão   |
| Pedro Oliveira     | Evangelismo   |

**⚠️ Observações:**
- A primeira linha é tratada como cabeçalho.
- O script ignora linhas vazias.
- Nomes duplicados ganham um sufixo numérico (ex: `JOAO_1.png`, `JOAO_2.png`).

---

## ⚙️ Configuração do Script

Caso precise ajustar as áreas de texto ou tamanhos iniciais, edite o arquivo `gerar.py`:

```python
# Nomes dos arquivos
MODELO = "modelo.png"
PLANILHA = "nomes.xlsx"
FONTE = "fonte.ttf"
SAIDA = "saida"

# Coordenadas das caixas de texto (x1, y1, x2, y2)
BOX_NOME = (110, 688, 571, 737)
BOX_EQUIPE = (110, 757, 571, 806)

# Tamanhos iniciais (o script reduz se não couber)
TAM_NOME_IDEAL = 40
TAM_EQUIPE_IDEAL = 34
```

---

## ▶️ Como Usar

1. Certifique-se de que todos os arquivos (`gerar.py`, `modelo.png`, `fonte.ttf`, `nomes.xlsx`) estão na mesma pasta.
2. Abra o terminal nesta pasta.
3. Execute o comando:

```bash
python gerar.py
```

### Exemplo de Saída:
```text
🎫 Gerador de Crachás - Iniciando...
✅ Planilha carregada: 81 registros encontrados
🔍 Calculando tamanhos de fonte ideais...
   Nome: 38px
   Equipe: 32px
🖨️ Gerando crachás...
============================================================
✅ Processo concluído!
============================================================
📁 Arquivos salvos em: 'saida/'
```

---

## 🎨 Diferenciais do Script

- **Padronização Global**: O script analisa todos os nomes primeiro para encontrar um tamanho de fonte que sirva para todos, evitando que um crachá tenha letra grande e outro pequena.
- **Sanitização**: Remove caracteres inválidos para nomes de arquivos.
- **Centralização Automática**: Textos são centralizados matematicamente nas coordenadas fornecidas.
- **Relatório de Erros**: Se algum dado estiver faltando na planilha, o script informa exatamente a linha do erro.

---

## ⚠️ Solução de Problemas

- **"No module named 'PIL'"**: Execute `pip install pillow`.
- **"No module named 'pandas'"**: Execute `pip install pandas openpyxl`.
- **Textos Cortados**: Verifique se as coordenadas em `BOX_NOME` e `BOX_EQUIPE` estão corretas ou reduza o `TAM_NOME_IDEAL`.

---

## 📄 Licença

Este projeto é de uso livre para fins pessoais ou comunitários. 🎉

---
**Esse projeto foi desenvolvido para automação do GMJ ❤️**

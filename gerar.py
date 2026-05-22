from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import os

# ============================================
# CONFIGURAÇÕES
# ============================================
MODELO = "modelo.png"
PLANILHA = "nomes.xlsx"
FONTE = "fonte.ttf"
SAIDA = "saida"

# Coordenadas CORRETAS das tags brancas (medidas da imagem)
BOX_NOME = (110, 688, 571, 737)      # Primeira caixa branca (nome)
BOX_EQUIPE = (110, 757, 571, 806)    # Segunda caixa branca (equipe)

# Tamanhos ideais de fonte
TAM_NOME_IDEAL = 40
TAM_EQUIPE_IDEAL = 34

# Margem interna
MARGEM_HORIZONTAL = 15
MARGEM_VERTICAL = 5

TAM_MINIMO = 16

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def largura_texto(draw, texto, fonte):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[2] - bbox[0]


def altura_texto(draw, texto, fonte):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[3] - bbox[1]


def descobrir_tamanho_global(lista_textos, tamanho_ideal, largura_max, altura_max):
    dummy_img = Image.new("RGB", (100, 100))
    draw = ImageDraw.Draw(dummy_img)
    
    tamanho_atual = tamanho_ideal
    
    while tamanho_atual >= TAM_MINIMO:
        fonte = ImageFont.truetype(FONTE, tamanho_atual)
        todos_cabem = True
        
        for texto in lista_textos:
            texto_limpo = str(texto).strip().upper()
            if not texto_limpo:
                continue
            
            largura = largura_texto(draw, texto_limpo, fonte)
            altura = altura_texto(draw, texto_limpo, fonte)
            
            if largura > largura_max or altura > altura_max:
                todos_cabem = False
                break
        
        if todos_cabem:
            return tamanho_atual
        
        tamanho_atual -= 1
    
    return TAM_MINIMO


def validar_arquivos():
    erros = []
    if not os.path.exists(MODELO):
        erros.append(f"❌ Modelo não encontrado: {MODELO}")
    if not os.path.exists(PLANILHA):
        erros.append(f"❌ Planilha não encontrada: {PLANILHA}")
    if not os.path.exists(FONTE):
        erros.append(f"❌ Fonte não encontrada: {FONTE}")
    
    if erros:
        for erro in erros:
            print(erro)
        return False
    return True


def sanitizar_nome_arquivo(nome):
    """Remove caracteres inválidos do nome do arquivo"""
    caracteres_invalidos = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    nome_limpo = nome
    for char in caracteres_invalidos:
        nome_limpo = nome_limpo.replace(char, '-')
    return nome_limpo


def main():
    print("🎫 Gerador de Crachás - Iniciando...\n")
    
    if not validar_arquivos():
        return
    
    os.makedirs(SAIDA, exist_ok=True)
    
    try:
        df = pd.read_excel(PLANILHA, dtype=str).fillna("")
        print(f"✅ Planilha carregada: {len(df)} registros encontrados\n")
    except Exception as e:
        print(f"❌ Erro ao carregar planilha: {e}")
        return
    
    if len(df) == 0:
        print("⚠️  Planilha vazia!")
        return
    
    # Calcula dimensões úteis das caixas
    largura_box_nome = BOX_NOME[2] - BOX_NOME[0] - (MARGEM_HORIZONTAL * 2)
    altura_box_nome = BOX_NOME[3] - BOX_NOME[1] - (MARGEM_VERTICAL * 2)
    
    largura_box_equipe = BOX_EQUIPE[2] - BOX_EQUIPE[0] - (MARGEM_HORIZONTAL * 2)
    altura_box_equipe = BOX_EQUIPE[3] - BOX_EQUIPE[1] - (MARGEM_VERTICAL * 2)
    
    print("🔍 Calculando tamanhos de fonte ideais...")
    
    tam_nome_final = descobrir_tamanho_global(
        df.iloc[:, 0],
        TAM_NOME_IDEAL,
        largura_box_nome,
        altura_box_nome
    )
    
    tam_equipe_final = descobrir_tamanho_global(
        df.iloc[:, 1],
        TAM_EQUIPE_IDEAL,
        largura_box_equipe,
        altura_box_equipe
    )
    
    print(f"   Nome: {tam_nome_final}px")
    print(f"   Equipe: {tam_equipe_final}px\n")
    
    fonte_nome = ImageFont.truetype(FONTE, tam_nome_final)
    fonte_equipe = ImageFont.truetype(FONTE, tam_equipe_final)
    
    # Calcula os centros das caixas (valores precisos em float)
    cx_nome = (BOX_NOME[0] + BOX_NOME[2]) / 2.0
    cy_nome = (BOX_NOME[1] + BOX_NOME[3]) / 2.0
    
    cx_equipe = (BOX_EQUIPE[0] + BOX_EQUIPE[2]) / 2.0
    cy_equipe = (BOX_EQUIPE[1] + BOX_EQUIPE[3]) / 2.0
    
    print("🖨️  Gerando crachás...")
    gerados = 0
    pulados = 0
    erros_detalhados = []
    
    for idx, linha in df.iterrows():
        try:
            nome = str(linha.iloc[0]).strip().upper()
            equipe = str(linha.iloc[1]).strip().upper()
            
            # Verifica se o nome está vazio
            if not nome or nome == "NAN" or nome == "":
                pulados += 1
                erros_detalhados.append({
                    'linha': idx + 2,  # +2 porque Excel começa em 1 e tem cabeçalho
                    'nome': linha.iloc[0],
                    'equipe': linha.iloc[1],
                    'motivo': 'Nome vazio ou inválido'
                })
                continue
            
            img = Image.open(MODELO).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Desenha textos centralizados
            draw.text(
                (cx_nome, cy_nome),
                nome,
                font=fonte_nome,
                fill="black",
                anchor="mm"
            )
            
            draw.text(
                (cx_equipe, cy_equipe),
                equipe,
                font=fonte_equipe,
                fill="black",
                anchor="mm"
            )
            
            # Salva com nome sanitizado
            nome_arquivo = sanitizar_nome_arquivo(nome)
            
            # Se o nome ficou vazio após sanitizar, usa o número da linha
            if not nome_arquivo or nome_arquivo.strip() == "":
                nome_arquivo = f"cracha_linha_{idx + 2}"
            
            caminho_saida = os.path.join(SAIDA, f"{nome_arquivo}.png")
            
            # Se já existe um arquivo com esse nome, adiciona número
            contador = 1
            caminho_original = caminho_saida
            while os.path.exists(caminho_saida):
                nome_sem_ext = os.path.splitext(caminho_original)[0]
                caminho_saida = f"{nome_sem_ext}_{contador}.png"
                contador += 1
            
            img.save(caminho_saida, "PNG", optimize=True)
            gerados += 1
            
        except Exception as e:
            pulados += 1
            erros_detalhados.append({
                'linha': idx + 2,
                'nome': linha.iloc[0] if len(linha) > 0 else "N/A",
                'equipe': linha.iloc[1] if len(linha) > 1 else "N/A",
                'motivo': str(e)
            })
    
    # Relatório final
    print(f"\n{'='*60}")
    print(f"✅ Processo concluído!")
    print(f"{'='*60}")
    print(f"   📊 Total de registros na planilha: {len(df)}")
    print(f"   ✅ Crachás gerados com sucesso: {gerados}")
    print(f"   ⚠️  Registros pulados/com erro: {pulados}")
    
    if erros_detalhados:
        print(f"\n{'='*60}")
        print(f"⚠️  DETALHES DOS REGISTROS NÃO PROCESSADOS:")
        print(f"{'='*60}")
        for erro in erros_detalhados:
            print(f"\n   Linha {erro['linha']} da planilha:")
            print(f"      Nome: '{erro['nome']}'")
            print(f"      Equipe: '{erro['equipe']}'")
            print(f"      Motivo: {erro['motivo']}")
    
    print(f"\n{'='*60}")
    print(f"📁 Arquivos salvos em: '{SAIDA}/'")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
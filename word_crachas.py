"""Folha de impressao dos crachas de saida/.

Monta PDF (300 dpi, pronto para imprimir) e DOCX editavel, numa grade que usa
o minimo de folhas sem cortar nenhuma foto: a foto entra inteira na caixa que o
usuario digita, o que sobra vira borda branca.

python word_crachas.py          # interface
python word_crachas.py --teste  # confere layout, contagem de folhas e arquivos
"""
import glob
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QDoubleSpinBox,
    QFileDialog, QMessageBox,
)

from gerar_crachas import MODERN_DARK_STYLE

PAGINA_MM = (210.0, 297.0)     # A4 retrato
DPI = 300                      # resolucao da folha impressa
QUALIDADE = 90
PISCOS_MM = 1.0                # respiro da linha da tabela no DOCX (nada e cortado)
FOLGA_LINHA_MM = 3.0           # folga extra por faixa no DOCX: o Google Docs ignora
                               # altura exata de linha e empurra faixa para a folha seguinte
MM_EMU = 36000                 # EMU por mm
MM_TW = 1440.0 / 25.4          # twips por mm
EXTENSOES = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
BASE = os.path.dirname(os.path.abspath(__file__))

DOC_INICIO = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"'
    ' xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    ' xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>'
)
DOC_FIM = (
    '<w:p><w:pPr><w:spacing w:line="20" w:lineRule="exact"/></w:pPr></w:p>'
    '<w:sectPr><w:pgSz w:w="{w}" w:h="{h}"/>'
    '<w:pgMar w:top="{m}" w:right="{m}" w:bottom="{m}" w:left="{m}"'
    ' w:header="0" w:footer="0" w:gutter="0"/>'
    '</w:sectPr></w:body></w:document>'
)


def _tw(mm):
    """Milimetros -> twips (1 polegada = 1440 twips = 25,4 mm)."""
    return int(round(mm * MM_TW))


def _px(mm, dpi=DPI):
    """Milimetros -> pixels na resolucao escolhida."""
    return max(1, int(round(mm / 25.4 * dpi)))


def listar(pasta):
    """Fotos da pasta, em ordem de nome."""
    return sorted(p for p in glob.glob(os.path.join(pasta, "*")) if p.lower().endswith(EXTENSOES))


def grade(largura, altura, margem=10.0, espaco=2.0, pagina=PAGINA_MM, folga_linha=0.0):
    """(colunas, linhas): a maior grade que cabe na folha sem girar nada.

    Sem rotacao a conta e fechada: cabe quantas colunas de (largura + espaco)
    cabem na area util. Nao ha busca a fazer, e nenhum layout cabe mais fotos.
    """
    uw, uh = pagina[0] - 2 * margem, pagina[1] - 2 * margem
    if min(largura, altura) <= 0:
        raise ValueError("Largura e altura precisam ser maiores que zero.")
    if largura > uw or altura > uh:
        raise ValueError(
            f"Cracha de {largura:g}x{altura:g} mm nao cabe na area util de "
            f"{uw:g}x{uh:g} mm. Diminua o cracha ou a margem da folha.")
    return (max(1, int((uw + espaco + 1e-9) // (largura + espaco))),
            max(1, int((uh + espaco + 1e-9) // (altura + espaco + folga_linha))))


def _rgb(img):
    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA", "P"):        # fundo branco em vez de preto
        img = img.convert("RGBA")
        fundo = Image.new("RGB", img.size, "white")
        fundo.paste(img, mask=img.split()[-1])
        return fundo
    return img.convert("RGB")


def cartao(caminho, largura, altura, dpi=DPI):
    """Imagem de exatamente (largura x altura) mm com a foto inteira dentro.

    A foto e reduzida proporcionalmente e centralizada; o que sobra da caixa
    vira borda branca. Nunca estica, nunca recorta.
    """
    img = _rgb(Image.open(caminho))
    alvo = (_px(largura, dpi), _px(altura, dpi))
    escala = min(alvo[0] / img.width, alvo[1] / img.height)
    img = img.resize((max(1, int(img.width * escala)), max(1, int(img.height * escala))),
                     Image.LANCZOS)
    fundo = Image.new("RGB", alvo, "white")
    fundo.paste(img, ((alvo[0] - img.width) // 2, (alvo[1] - img.height) // 2))
    return fundo


def folhas(caminhos, largura, altura, margem=10.0, espaco=2.0, pagina=PAGINA_MM, dpi=DPI):
    """Gera (folha A4, retangulos dos crachas em px) uma folha por vez.

    dpi menor que 300 serve so para a pre-visualizacao na tela.
    """
    colunas, linhas = grade(largura, altura, margem, espaco, pagina)
    uw, uh = pagina[0] - 2 * margem, pagina[1] - 2 * margem
    bloco_w = colunas * largura + (colunas - 1) * espaco
    bloco_h = linhas * altura + (linhas - 1) * espaco
    px_m, px_l = _px(margem, dpi), _px(largura, dpi)
    px_a, px_e = _px(altura, dpi), _px(espaco, dpi)
    x0 = px_m + _px((uw - bloco_w) / 2, dpi)
    y0 = px_m + _px((uh - bloco_h) / 2, dpi)
    tam = (_px(pagina[0], dpi), _px(pagina[1], dpi))

    itens = list(caminhos)
    for inicio in range(0, len(itens), colunas * linhas):
        folha = Image.new("RGB", tam, "white")
        retangulos = []
        for k, caminho in enumerate(itens[inicio:inicio + colunas * linhas]):
            i, j = divmod(k, colunas)
            x, y = x0 + j * (px_l + px_e), y0 + i * (px_a + px_e)
            folha.paste(cartao(caminho, largura, altura, dpi), (x, y))
            retangulos.append((x, y, px_l, px_a))
        yield folha, retangulos


def _escrever_pdf(destino, folhas_iter):
    """PDF minimo, uma folha por vez, sem o arquivo inteiro na memoria.

    O save_all do Pillow guardaria todas as folhas (26 MB cada a 300 dpi) e o
    append dele reescreve o catalogo a cada pagina, entao o PDF e montado aqui.
    """
    with open(destino, "wb") as f:
        f.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets, paginas, proximo = {}, [], 3

        def obj(numero, corpo):
            offsets[numero] = f.tell()
            f.write(b"%d 0 obj\n" % numero + corpo + b"\nendobj\n")

        for folha, _ in folhas_iter:
            larg_pt, alt_pt = folha.width * 72.0 / DPI, folha.height * 72.0 / DPI
            buf = BytesIO()
            folha.save(buf, "JPEG", quality=QUALIDADE)
            jpeg = buf.getvalue()
            paginas.append(proximo)
            obj(proximo, ("<</Type/Page/Parent 2 0 R/Resources<</XObject<</Im0 %d 0 R>>"
                          ">>/MediaBox[0 0 %.2f %.2f]/Contents %d 0 R>>"
                          % (proximo + 2, larg_pt, alt_pt, proximo + 1)).encode())
            conteudo = b"q %.2f 0 0 %.2f 0 0 cm /Im0 Do Q" % (larg_pt, alt_pt)
            obj(proximo + 1, b"<</Length %d>>stream\n" % len(conteudo)
                + conteudo + b"\nendstream")
            obj(proximo + 2, b"<</Type/XObject/Subtype/Image/Width %d/Height %d"
                            b"/ColorSpace/DeviceRGB/BitsPerComponent 8/Filter/DCTDecode"
                            b"/Length %d>>stream\n" % (folha.width, folha.height, len(jpeg))
                + jpeg + b"\nendstream")
            proximo += 3

        obj(2, ("<</Type/Pages/Kids[%s]/Count %d>>"
                % (" ".join("%d 0 R" % p for p in paginas), len(paginas))).encode())
        obj(1, b"<</Type/Catalog/Pages 2 0 R>>")
        inicio_xref, total = f.tell(), max(offsets) + 1
        f.write(b"xref\n0 %d\n0000000000 65535 f \n" % total)
        f.write(b"".join(b"%010d 00000 n \n" % offsets[i] for i in range(1, total)))
        f.write(b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n"
                % (total, inicio_xref))
    return len(paginas)


def gerar_pdf(caminhos, largura, altura, margem=10.0, espaco=2.0,
              destino=None, pagina=PAGINA_MM):
    """PDF de impressao, uma folha A4 por pagina. Devolve (folhas, caminho)."""
    itens = list(caminhos)
    if not itens:
        raise ValueError("Nenhuma imagem encontrada.")
    destino = destino or os.path.join(BASE, "saida", "crachas.pdf")
    return _escrever_pdf(destino, folhas(itens, largura, altura, margem, espaco, pagina)), destino


def _imagem_xml(rid, larg_mm, alt_mm, docpr, nome):
    cx, cy = int(larg_mm * MM_EMU), int(alt_mm * MM_EMU)
    return (
        '<w:r><w:rPr><w:noProof/></w:rPr><w:drawing>'
        '<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{docpr}" name="{nome}"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{docpr}" name="{nome}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
    )


def _celula_xml(rid, larg_mm, alt_mm, docpr, nome, meia_tw):
    return (
        f'<w:tc><w:tcPr><w:tcW w:w="{_tw(larg_mm)}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="{_tw(alt_mm)}"'
        f' w:lineRule="exact"/>'
        f'<w:ind w:left="{meia_tw}" w:right="{meia_tw}"/><w:jc w:val="center"/></w:pPr>'
        f'{_imagem_xml(rid, larg_mm, alt_mm, docpr, nome)}</w:p></w:tc>'
    )


def _tabela_xml(linhas, colunas, larg_col_tw, larg_tab_tw, indent_tw, meia_tw):
    sem_borda = "".join(f'<w:{b} w:val="none" w:sz="0" w:space="0"/>'
                        for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    grid = '<w:gridCol w:w="%d"/>' % larg_col_tw * max(1, colunas)
    return (
        f'<w:tbl><w:tblPr><w:tblW w:w="{larg_tab_tw}" w:type="dxa"/>'
        f'<w:tblInd w:w="{indent_tw}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
        f'<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="{meia_tw}" w:type="dxa"/>'
        f'<w:bottom w:w="0" w:type="dxa"/><w:right w:w="{meia_tw}" w:type="dxa"/></w:tblCellMar>'
        f'<w:tblBorders>{sem_borda}</w:tblBorders></w:tblPr>'
        f'<w:tblGrid>{grid}</w:tblGrid>{"".join(linhas)}</w:tbl>'
    )


def _jpeg(cartao_png):
    buf = BytesIO()
    cartao_png.save(buf, "JPEG", quality=QUALIDADE, dpi=(DPI, DPI))
    return buf.getvalue()


def gerar_docx(caminhos, largura, altura, margem=10.0, espaco=2.0,
                destino=None, pagina=PAGINA_MM):
    """DOCX com um cracha por celula, editavel. Devolve (folhas, caminho).

    Linhas com FOLGA_LINHA_MM a mais porque o Google Docs ignora a altura exata
    e empurraria faixa para a folha seguinte. Para imprimir, use o PDF.
    """
    itens = list(caminhos)
    if not itens:
        raise ValueError("Nenhuma imagem encontrada.")
    destino = destino or os.path.join(BASE, "saida", "crachas.docx")

    colunas, linhas = grade(largura, altura, margem, espaco, pagina, FOLGA_LINHA_MM)
    uw = pagina[0] - 2 * margem
    bloco_w = colunas * largura + (colunas - 1) * espaco
    indent = max(0.0, (uw - bloco_w) / 2)
    meia_tw = _tw(espaco / 2)
    altura_linha = altura + PISCOS_MM

    paginas, restantes = [], itens
    while restantes:
        lote = restantes[:colunas * linhas]
        restantes = restantes[colunas * linhas:]
        paginas.append(lote)

    corpo, relacoes, midia, docpr = [], [], [], 0
    for indice, lote in enumerate(paginas):
        if indice:
            corpo.append('<w:p><w:pPr><w:spacing w:line="20" w:lineRule="exact"/></w:pPr>'
                         '<w:r><w:br w:type="page"/></w:r></w:p>')
        linhas_xml = []
        for i in range(linhas):
            faixa = lote[i * colunas:(i + 1) * colunas]
            if not faixa:
                break
            celulas = []
            for caminho in faixa:
                docpr += 1
                nome_media = f"cracha{len(midia) + 1}.jpg"
                rid = f"rId{len(midia) + 1}"
                midia.append((nome_media, _jpeg(cartao(caminho, largura, altura))))
                relacoes.append(
                    f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
                    f'officeDocument/2006/relationships/image" Target="media/{nome_media}"/>'
                )
                celulas.append(_celula_xml(rid, largura, altura_linha, docpr,
                                           os.path.basename(caminho), meia_tw))
            linhas_xml.append(f'<w:tr><w:trPr><w:trHeight w:val="{_tw(altura_linha)}"'
                              f' w:hRule="exact"/><w:cantSplit/></w:trPr>'
                              f'{"".join(celulas)}</w:tr>')
        corpo.append(_tabela_xml(linhas_xml, colunas, _tw(largura + espaco),
                                 _tw(bloco_w), _tw(indent), meia_tw))

    doc = DOC_INICIO + "".join(corpo) + DOC_FIM.format(
        w=_tw(pagina[0]), h=_tw(pagina[1]), m=_tw(margem))
    ET.fromstring(doc)   # falha aqui se o XML sair malformado

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="jpg" ContentType="image/jpeg"/>'
        '<Default Extension="jpeg" ContentType="image/jpeg"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
        'officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    raiz_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(relacoes) + "</Relationships>"
    )

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", raiz_rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/document.xml", doc)
        for nome_media, dados in midia:
            z.writestr(f"word/media/{nome_media}", dados)

    return len(paginas), destino


DPI_PREVIA = 72                # so a pre-visualizacao na tela


def _pixmap(img):
    """PIL -> QPixmap (o .copy() solta o buffer do Pillow antes de sumir)."""
    dados = img.tobytes("raw", "RGB")
    qimg = QImage(dados, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())


def testar():
    import tempfile
    from PIL import ImageChops

    def area_da_foto(cartao_png):
        return ImageChops.difference(cartao_png, Image.new("RGB", cartao_png.size, "white")).getbbox()

    with tempfile.TemporaryDirectory() as tmp:
        pasta = os.path.join(tmp, "saida")
        os.makedirs(pasta)
        for i in range(76):                       # mesmo formato do modelo.png
            Image.new("RGB", (681, 1021), (i * 3 % 255, 90, 160)).save(
                os.path.join(pasta, f"cracha_{i:03d}.png"))
        caminhos = listar(pasta)
        assert len(caminhos) == 76, len(caminhos)
        deitado = os.path.join(tmp, "deitado.png")
        Image.new("RGB", (1021, 681), (10, 90, 160)).save(deitado)

        larg, alt, margem, espaco = 54.0, 86.0, 10.0, 2.0
        colunas, linhas = grade(larg, alt, margem, espaco)
        assert (colunas, linhas) == (3, 3), (colunas, linhas)
        assert len(list(folhas(caminhos, larg, alt, margem, espaco))) == math.ceil(76 / 9)

        # nenhuma foto fora da folha, nenhuma sobreposta, nenhuma esticada
        tam = (_px(PAGINA_MM[0]), _px(PAGINA_MM[1]))
        usadas, folhas_geradas = 0, 0
        for folha, rects in folhas(caminhos, larg, alt, margem, espaco):
            folhas_geradas += 1
            assert folha.size == tam, folha.size
            for x, y, w, h in rects:
                assert 0 <= x and 0 <= y and x + w <= tam[0] and y + h <= tam[1], (x, y, w, h)
                assert (w, h) == (_px(larg), _px(alt)), (w, h)   # cartao inteiro, sem corte
            for a in range(len(rects)):
                for b in range(a + 1, len(rects)):
                    ax, ay, aw, ah = rects[a]
                    bx, by, bw, bh = rects[b]
                    assert ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay, \
                        (rects[a], rects[b])
            usadas += len(rects)
        assert usadas == 76, usadas
        assert folhas_geradas == math.ceil(76 / (colunas * linhas))

        # o cracha e a foto inteira com borda branca: 54x86 na caixa, sem esticar
        # (foto alta em caixa alta -> borda em cima/baixo; foto deitada -> nos lados)
        for caminho_ref, rotulo in ((caminhos[0], "em pe"), (deitado, "deitada")):
            c = cartao(caminho_ref, larg, alt)
            assert c.size == (_px(larg), _px(alt)), c.size
            iw, ih = Image.open(caminho_ref).size
            x0, y0, x1, y1 = area_da_foto(c)
            assert abs(((x1 - x0) / (y1 - y0)) / (iw / ih) - 1) < 0.01, f"foto esticada ({rotulo})"
            branco = (255, 255, 255)
            if x0: assert c.getpixel((x0 - 1, c.height // 2)) == branco, rotulo
            if x1 < c.width: assert c.getpixel((x1, c.height // 2)) == branco, rotulo
            if y0: assert c.getpixel((c.width // 2, y0 - 1)) == branco, rotulo
            if y1 < c.height: assert c.getpixel((c.width // 2, y1)) == branco, rotulo
            assert (x0 <= 1 and x1 >= c.width - 1) or (y0 <= 1 and y1 >= c.height - 1), \
                f"foto pequena dentro da caixa demais ({rotulo})"

        # PDF com a contagem certa de folhas e estrutura valida
        n_pdf, pdf = gerar_pdf(caminhos, larg, alt, margem, espaco,
                               os.path.join(tmp, "crachas.pdf"))
        assert n_pdf == folhas_geradas
        with open(pdf, "rb") as f:
            dados = f.read()
        assert dados.startswith(b"%PDF-") and dados.rstrip().endswith(b"%%EOF")
        assert len(re.findall(rb"/Type/Page\b", dados)) == folhas_geradas
        assert re.search(rb"/Count\s+%d\b" % folhas_geradas, dados)
        assert len(re.findall(rb"/MediaBox\[0 0 595\.20 841\.92\]", dados)) == folhas_geradas
        inicio = int(re.search(rb"startxref\s+(\d+)", dados).group(1))
        tabela = dados[inicio:].split(b"\n")
        assert tabela[0] == b"xref" and int(tabela[1].split()[1]) == max(
            int(o.split()[0]) for o in re.findall(rb"(?m)^\d+ 0 obj", dados)) + 1
        for numero in range(1, int(tabela[1].split()[1])):
            offset = int(tabela[2 + numero].split()[0])
            assert dados[offset:].startswith(b"%d 0 obj" % numero), (numero, offset)

        # DOCX: um desenho por cracha, uma tabela por folha
        n_docx, docx_path = gerar_docx(caminhos, larg, alt, margem, espaco,
                                       os.path.join(tmp, "crachas.docx"))
        with zipfile.ZipFile(docx_path) as z:
            assert z.testzip() is None
            doc = z.read("word/document.xml").decode()
        assert doc.count("<w:drawing>") == 76, doc.count("<w:drawing>")
        assert doc.count("<w:tbl>") == n_docx
        assert doc.count('w:br w:type="page"') == n_docx - 1
        for frag in doc.split("<wp:extent ")[1:]:
            cx = int(frag.split('cx="')[1].split('"')[0]) / MM_EMU
            cy = int(frag.split('cy="')[1].split('"')[0]) / MM_EMU
            assert abs(cx - larg) < 0.1 and abs(cy - (alt + PISCOS_MM)) < 0.1, (cx, cy)

        print("OK: 76 fotos, %d folha(s) de %d, PDF %d KB, DOCX %d KB"
              % (folhas_geradas, colunas * linhas,
                 os.path.getsize(pdf) // 1024, os.path.getsize(docx_path) // 1024))
    return True


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Imprimir Crachas")
        self.setMinimumSize(560, 460)
        saida = os.path.join(BASE, "saida")

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(16, 16, 16, 16)
        raiz.setSpacing(12)
        raiz.addWidget(QLabel("Fotos da pasta saida/ prontas para imprimir",
                              objectName="titleLabel"))

        arquivos = QGroupBox("Arquivos")
        arq = QVBoxLayout(arquivos)
        self._ed_pasta = QLineEdit(saida)
        self._ed_pasta.setReadOnly(True)
        self._ed_pdf = QLineEdit(os.path.join(saida, "crachas.pdf"))
        self._ed_docx = QLineEdit(os.path.join(saida, "crachas.docx"))
        self._ed_pdf.setReadOnly(True)
        self._ed_docx.setReadOnly(True)
        b_pasta = QPushButton("Escolher pasta das fotos")
        b_pasta.clicked.connect(self._escolher_pasta)
        b_pdf = QPushButton("Escolher arquivo do PDF")
        b_pdf.clicked.connect(lambda: self._escolher_saida(self._ed_pdf, "PDF (*.pdf)"))
        b_docx = QPushButton("Escolher arquivo do Word")
        b_docx.clicked.connect(lambda: self._escolher_saida(self._ed_docx, "Word (*.docx)"))
        for rotulo, widget in (("Fotos:", self._ed_pasta), ("PDF:", self._ed_pdf),
                               ("Word:", self._ed_docx)):
            linha = QHBoxLayout()
            linha.addWidget(QLabel(rotulo))
            linha.addWidget(widget, stretch=1)
            arq.addLayout(linha)
        for b in (b_pasta, b_pdf, b_docx):
            arq.addWidget(b)
        raiz.addWidget(arquivos)

        medidas = QGroupBox("Medidas em mm (papel A4)")
        med = QHBoxLayout(medidas)
        self._sp = {}
        for chave, rotulo, valor, maximo in (
            ("largura", "Largura", 54.0, 210.0),
            ("altura", "Altura", 86.0, 297.0),
            ("espaco", "Espaco entre", 2.0, 50.0),
            ("margem", "Margem da folha", 10.0, 50.0),
        ):
            caixa = QVBoxLayout()
            spin = QDoubleSpinBox()
            spin.setRange(1.0 if chave in ("largura", "altura") else 0.0, maximo)
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setValue(valor)
            spin.valueChanged.connect(self._previa)
            caixa.addWidget(QLabel(rotulo))
            caixa.addWidget(spin)
            med.addLayout(caixa)
            self._sp[chave] = spin
        raiz.addWidget(medidas)

        self._lbl = QLabel("")
        self._lbl.setWordWrap(True)
        raiz.addWidget(self._lbl)

        self._imagem = QLabel()
        self._imagem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._imagem.setStyleSheet("background-color: #f8fafc; border: 1px solid #334155;")
        raiz.addWidget(self._imagem, stretch=1)

        b_gerar = QPushButton("Gerar PDF e Word", objectName="successBtn")
        b_gerar.clicked.connect(self._gerar)
        raiz.addWidget(b_gerar)
        self.statusBar().showMessage("Pronto.")

        self._previa()

    def _escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Pasta das fotos", self._ed_pasta.text())
        if pasta:
            self._ed_pasta.setText(pasta)
            self._previa()

    def _escolher_saida(self, campo, filtro):
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar", campo.text(), filtro)
        if caminho:
            campo.setText(caminho)

    def _medidas(self):
        return (self._sp["largura"].value(), self._sp["altura"].value(),
                self._sp["margem"].value(), self._sp["espaco"].value())

    def _previa(self):
        """Conta as folhas e mostra a primeira antes de gerar."""
        folha = None
        try:
            itens = listar(self._ed_pasta.text())
            larg, alt, margem, espaco = self._medidas()
            colunas, linhas = grade(larg, alt, margem, espaco)
            por_folha = colunas * linhas
            texto = (f"{len(itens)} foto(s) -> {math.ceil(len(itens) / por_folha) if itens else 0}"
                     f" folha(s)  |  {por_folha} por folha ({colunas} x {linhas})")
            folha, _ = next(iter(folhas(itens[:por_folha], larg, alt, margem, espaco,
                                        dpi=DPI_PREVIA)), (None, None))
        except Exception as e:
            texto = f"ERRO: {e}"
        self._lbl.setText(texto)
        self._imagem.clear()
        if folha is not None:
            folha.thumbnail((400, 560), Image.LANCZOS)
            self._imagem.setPixmap(_pixmap(folha))

    def _gerar(self):
        itens = listar(self._ed_pasta.text())
        larg, alt, margem, espaco = self._medidas()
        try:
            folhas_pdf, destino_pdf = gerar_pdf(itens, larg, alt, margem, espaco,
                                                self._ed_pdf.text())
            folhas_docx, destino_docx = gerar_docx(itens, larg, alt, margem, espaco,
                                                  self._ed_docx.text())
        except Exception as e:
            QMessageBox.critical(self, "Erro", str(e))
            return
        self.statusBar().showMessage(f"{destino_pdf}", 5000)
        QMessageBox.information(
            self, "Pronto",
            f"{len(itens)} foto(s)\n\n"
            f"PDF: {destino_pdf} ({folhas_pdf} folha(s))\n"
            f"Word: {destino_docx} ({folhas_docx} folha(s))\n\n"
            "Imprima pelo PDF. O Word serve para conferir ou editar.")


def main():
    if "--teste" in sys.argv:
        sys.exit(0 if testar() else 1)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_DARK_STYLE)
    janela = MainWindow()
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
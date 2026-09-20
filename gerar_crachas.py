import sys
import os
import re
import pandas as pd
import unicodedata
from PIL import Image, ImageDraw, ImageFont

EQUIPES_CONHECIDAS = [
    "Intercessão", "Círculo", "Animação", "Cozinha",
    "Ordem", "Acolhida", "Mídias", "Música",
]

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QScrollArea, QLabel, QFileDialog,
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QSizePolicy, QStatusBar, QMessageBox, QFrame, QRadioButton,
    QButtonGroup, QProgressBar, QGroupBox
)
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QColor, QFont, QKeySequence, QShortcut
)

MODERN_DARK_STYLE = """
QMainWindow {
    background-color: #0f172a;
}
QWidget#centralWidget {
    background-color: #0f172a;
}
QFrame#rightPanel {
    background-color: #1e293b;
    border-left: 1px solid #334155;
}
QGroupBox {
    color: #94a3b8;
    font-weight: bold;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLabel {
    color: #f8fafc;
    font-size: 13px;
}
QLabel#titleLabel {
    color: #f8fafc;
    font-size: 16px;
    font-weight: bold;
}
QTextEdit {
    background-color: #020617;
    color: #38bdf8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QPushButton {
    background-color: #334155;
    color: #f8fafc;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #475569;
}
QPushButton:pressed {
    background-color: #1e293b;
}
QPushButton#primaryBtn {
    background-color: #0284c7;
    color: #ffffff;
}
QPushButton#primaryBtn:hover {
    background-color: #0369a1;
}
QPushButton#successBtn {
    background-color: #16a34a;
    color: #ffffff;
    font-size: 14px;
    padding: 12px;
}
QPushButton#successBtn:hover {
    background-color: #15803d;
}
QRadioButton {
    color: #f8fafc;
    spacing: 8px;
    font-weight: 500;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 8px;
    border: 2px solid #64748b;
}
QRadioButton::indicator:checked {
    border-color: #38bdf8;
    background-color: #38bdf8;
}
QScrollArea {
    background-color: #020617;
    border: none;
}
QStatusBar {
    background-color: #0f172a;
    color: #94a3b8;
    border-top: 1px solid #334155;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 4px;
    text-align: center;
    color: white;
    background-color: #020617;
}
QProgressBar::chunk {
    background-color: #0284c7;
}
"""


class Canvas(QLabel):
    rectangle_drawn = Signal(QRect)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._pixmap = None
        self._original_size = (0, 0)
        self._scale = 1.0

        self._drawing = False
        self._start = QPoint()
        self._current = QPoint()
        self._rects = {}
        self._active_mode = "NOME"
        self._overlay_rects = []

    def set_image(self, pixmap):
        self._pixmap = pixmap
        self._original_size = (pixmap.width(), pixmap.height())
        self._refresh()

    def set_mode(self, mode):
        self._active_mode = mode

    def clear_rect(self, key):
        self._rects.pop(key, None)
        self._rebuild_overlay()
        self.update()

    def clear_all(self):
        self._rects.clear()
        self._overlay_rects.clear()
        self.update()

    def _refresh(self):
        if self._pixmap:
            scaled = self._pixmap.scaled(
                self.viewport_width(), self.viewport_height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._scale = self._original_size[0] / scaled.width() if scaled.width() else 1.0
            self.setPixmap(scaled)

    def viewport_width(self):
        parent = self.parent()
        return parent.viewport().width() if parent and hasattr(parent, 'viewport') else self.width()

    def viewport_height(self):
        parent = self.parent()
        return parent.viewport().height() if parent and hasattr(parent, 'viewport') else self.height()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pixmap:
            self._drawing = True
            self._start = event.position().toPoint()
            self._current = self._start
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drawing:
            self._current = event.position().toPoint()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            self._current = event.position().toPoint()

            display_rect = QRect(self._start, self._current).normalized()
            if display_rect.width() > 5 and display_rect.height() > 5:
                self._rects[self._active_mode] = display_rect
                self._rebuild_overlay()

                ox1 = int(display_rect.left() * self._scale)
                oy1 = int(display_rect.top() * self._scale)
                ox2 = int(display_rect.right() * self._scale)
                oy2 = int(display_rect.bottom() * self._scale)
                self.rectangle_drawn.emit(QRect(ox1, oy1, ox2 - ox1, oy2 - oy1))

            self.update()
        super().mouseReleaseEvent(event)

    def _rebuild_overlay(self):
        self._overlay_rects = []
        for key in ("NOME", "EQUIPE"):
            if key in self._rects:
                self._overlay_rects.append((self._rects[key], key))

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._pixmap:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = {"NOME": QColor(74, 222, 128), "EQUIPE": QColor(56, 189, 248)}
        fills = {"NOME": QColor(74, 222, 128, 40), "EQUIPE": QColor(56, 189, 248, 40)}

        for rect, key in self._overlay_rects:
            painter.setPen(QPen(colors[key], 2))
            painter.fillRect(rect, fills[key])
            painter.drawRect(rect)

            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.setPen(colors[key])
            painter.drawText(rect.topLeft() + QPoint(4, -6), key)

        if self._drawing:
            color = colors.get(self._active_mode, QColor(251, 113, 133))
            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            drag_rect = QRect(self._start, self._current).normalized()
            painter.drawRect(drag_rect)

        painter.end()

    def get_original_coords(self, key):
        if key not in self._rects:
            return None
        r = self._rects[key]
        return (
            int(r.left() * self._scale),
            int(r.top() * self._scale),
            int(r.right() * self._scale),
            int(r.bottom() * self._scale)
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mapeador de Coordenadas e Gerador de Crachás")
        self.setMinimumSize(1100, 750)

        self._image_path = None
        self._planilha_path = None
        self._fonte_path = None
        self._saida_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida")
        os.makedirs(self._saida_dir, exist_ok=True)
        self._build_ui()
        self._setup_shortcuts()
        self.statusBar().showMessage("Pronto. Importe uma imagem de modelo para comecar.")

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Canvas Area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._canvas = Canvas(self._scroll)
        self._scroll.setWidget(self._canvas)
        main_layout.addWidget(self._scroll, stretch=1)

        # Sidebar Panel
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(12)

        # Title
        right_layout.addWidget(QLabel("Mapeador de Crachás", objectName="titleLabel"))

        # Image Load Section
        btn_open = QPushButton("Carregar Modelo (Imagem)", objectName="primaryBtn")
        btn_open.clicked.connect(self._open_file)
        right_layout.addWidget(btn_open)

        # File Selection Section
        files_box = QGroupBox("Arquivos")
        files_layout = QVBoxLayout(files_box)
        files_layout.setSpacing(8)

        self._lbl_planilha = QLabel("Nenhuma planilha selecionada")
        self._lbl_planilha.setStyleSheet("color: #94a3b8; font-size: 11px;")
        btn_planilha = QPushButton("Selecionar Planilha (.xlsx)")
        btn_planilha.clicked.connect(self._select_planilha)
        files_layout.addWidget(btn_planilha)
        files_layout.addWidget(self._lbl_planilha)

        self._lbl_fonte = QPushButton("Selecionar Fonte (.ttf)")
        self._lbl_fonte.clicked.connect(self._select_fonte)
        files_layout.addWidget(self._lbl_fonte)
        self._lbl_fonte_info = QLabel("Nenhuma fonte selecionada")
        self._lbl_fonte_info.setStyleSheet("color: #94a3b8; font-size: 11px;")
        files_layout.addWidget(self._lbl_fonte_info)

        self._lbl_saida = QLabel(f"Saida: {self._saida_dir}")
        self._lbl_saida.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._lbl_saida.setWordWrap(True)
        files_layout.addWidget(self._lbl_saida)

        right_layout.addWidget(files_box)

        # Validation Panel
        self._validacao_box = QGroupBox("Validacao da Planilha")
        validacao_layout = QVBoxLayout(self._validacao_box)
        self._lbl_validacao = QLabel("Nenhuma planilha carregada")
        self._lbl_validacao.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self._lbl_validacao.setWordWrap(True)
        validacao_layout.addWidget(self._lbl_validacao)
        right_layout.addWidget(self._validacao_box)
        self._validacao_box.setVisible(False)

        # Selection Group Mode
        mode_group_box = QGroupBox("Camada de Seleção")
        mode_layout = QVBoxLayout(mode_group_box)
        
        self._radio_nome = QRadioButton("Mapear Nome (1)")
        self._radio_equipe = QRadioButton("Mapear Equipe (2)")
        self._radio_nome.setChecked(True)

        self._bg_mode = QButtonGroup(self)
        self._bg_mode.addButton(self._radio_nome, 1)
        self._bg_mode.addButton(self._radio_equipe, 2)
        self._bg_mode.idToggled.connect(self._on_mode_changed)

        mode_layout.addWidget(self._radio_nome)
        mode_layout.addWidget(self._radio_equipe)
        right_layout.addWidget(mode_group_box)

        # Output Box
        coords_box = QGroupBox("Coordenadas Obtidas")
        coords_layout = QVBoxLayout(coords_box)
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        coords_layout.addWidget(self._output)

        btn_copy = QPushButton("Copiar Mapeamento")
        btn_copy.clicked.connect(self._copy_to_clipboard)
        coords_layout.addWidget(btn_copy)
        right_layout.addWidget(coords_box)

        # Clear Controls
        clear_layout = QHBoxLayout()
        btn_clear_active = QPushButton("Limpar Atual")
        btn_clear_active.clicked.connect(self._clear_current)
        btn_clear_all = QPushButton("Limpar Tudo")
        btn_clear_all.clicked.connect(self._clear_all)
        clear_layout.addWidget(btn_clear_active)
        clear_layout.addWidget(btn_clear_all)
        right_layout.addLayout(clear_layout)

        right_layout.addStretch()

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        right_layout.addWidget(self._progress_bar)

        # Action Trigger
        btn_gerar = QPushButton("Gerar Crachás", objectName="successBtn")
        btn_gerar.clicked.connect(self._gerar_crachas)
        right_layout.addWidget(btn_gerar)

        main_layout.addWidget(right_panel)
        self._canvas.rectangle_drawn.connect(self._on_rect_drawn)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+O"), self, self._open_file)
        QShortcut(QKeySequence("Ctrl+C"), self, self._copy_to_clipboard)
        QShortcut(QKeySequence("1"), self, lambda: self._radio_nome.setChecked(True))
        QShortcut(QKeySequence("2"), self, lambda: self._radio_equipe.setChecked(True))

    def _on_mode_changed(self, id_, checked):
        if checked:
            mode = "NOME" if id_ == 1 else "EQUIPE"
            self._canvas.set_mode(mode)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir imagem", "", "Imagens (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.statusBar().showMessage("Falha ao abrir a imagem selecionada.")
                return
            self._image_path = path
            self._canvas.set_image(pixmap)
            self.statusBar().showMessage(f"Arquivo: {os.path.basename(path)} ({pixmap.width()}x{pixmap.height()}px)")

    def _select_planilha(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Planilha", "", "Excel (*.xlsx *.xls)"
        )
        if path:
            self._planilha_path = path
            self._lbl_planilha.setText(os.path.basename(path))
            self._lbl_planilha.setStyleSheet("color: #f8fafc; font-size: 11px;")
            self._validar_planilha(path)

    def _normalizar_acentos(self, texto):
        nfkd = unicodedata.normalize("NFKD", texto)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def _regex_equipes(self):
        padroes = []
        for eq in EQUIPES_CONHECIDAS:
            sem = self._normalizar_acentos(eq)
            padroes.append(re.escape(eq))
            if sem != eq:
                padroes.append(re.escape(sem))
        return re.compile("|".join(padroes), re.IGNORECASE)

    def _validar_planilha(self, path):
        try:
            df = pd.read_excel(path, dtype=str).fillna("")
        except Exception as e:
            self._validacao_box.setVisible(True)
            self._lbl_validacao.setText(f"Erro ao ler: {e}")
            self._lbl_validacao.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold;")
            return

        if len(df.columns) < 2:
            self._validacao_box.setVisible(True)
            self._lbl_validacao.setText("Planilha precisa de pelo menos 2 colunas (Nome, Equipe).")
            self._lbl_validacao.setStyleSheet("color: #f87171; font-size: 11px; font-weight: bold;")
            return

        total = len(df)
        vazios_nome = 0
        vazios_equipe = 0
        duplicados = []
        suspeitos = []
        regex = self._regex_equipes()

        nomes_normalizados = []
        for idx, row in df.iterrows():
            nome = str(row.iloc[0]).strip().upper() if len(row) > 0 else ""
            equipe = str(row.iloc[1]).strip().upper() if len(row) > 1 else ""

            if not nome or nome == "NAN":
                vazios_nome += 1
                continue
            if not equipe or equipe == "NAN":
                vazios_equipe += 1

            nomes_normalizados.append((idx, nome))

            if regex.search(nome) and equipe:
                suspeitos.append(f"  Linha {idx + 2}: '{nome}' - pode ter equipe no nome")

        vistos = {}
        for idx, nome in nomes_normalizados:
            if nome in vistos:
                duplicados.append(f"  '{nome}' (linhas {vistos[nome] + 2} e {idx + 2})")
            else:
                vistos[nome] = idx

        problemas = []
        if vazios_nome:
            problemas.append(f"  {vazios_nome} nome(s) vazio(s)")
        if vazios_equipe:
            problemas.append(f"  {vazios_equipe} equipe(s) vazia(s)")
        if duplicados:
            problemas.append(f"  {len(duplicados)} nome(s) duplicado(s):")
            problemas.extend(duplicados)
        if suspeitos:
            problemas.append(f"  {len(suspeitos)} nome(s) suspeito(s):")
            problemas.extend(suspeitos)

        self._validacao_box.setVisible(True)
        if not problemas:
            self._lbl_validacao.setText(f"Total: {total} registros\nTudo certo!")
            self._lbl_validacao.setStyleSheet("color: #4ade80; font-size: 11px; font-weight: bold;")
        else:
            texto = f"Total: {total} registros\n" + "\n".join(problemas)
            self._lbl_validacao.setText(texto)
            cor = "#fbbf24" if not vazios_nome else "#f87171"
            self._lbl_validacao.setStyleSheet(f"color: {cor}; font-size: 11px;")

    def _select_fonte(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Fonte", "", "Fontes (*.ttf *.otf)"
        )
        if path:
            self._fonte_path = path
            self._lbl_fonte_info.setText(os.path.basename(path))
            self._lbl_fonte_info.setStyleSheet("color: #f8fafc; font-size: 11px;")

    def _on_rect_drawn(self, rect):
        parts = []
        for key in ("NOME", "EQUIPE"):
            coords = self._canvas.get_original_coords(key)
            if coords:
                parts.append(f"BOX_{key} = {coords}")
        self._output.setPlainText("\n".join(parts))

    def _copy_to_clipboard(self):
        text = self._output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage("Coordenadas copiadas para a área de transferência.", 3000)

    def _clear_current(self):
        mode = "NOME" if self._radio_nome.isChecked() else "EQUIPE"
        self._canvas.clear_rect(mode)
        self._on_rect_drawn(None)

    def _clear_all(self):
        self._canvas.clear_all()
        self._output.clear()

    def _gerar_crachas(self):
        coords_nome = self._canvas.get_original_coords("NOME")
        coords_equipe = self._canvas.get_original_coords("EQUIPE")

        if not coords_nome or not coords_equipe:
            QMessageBox.warning(self, "Aviso", "Desenhe ambas as caixas (NOME e EQUIPE) antes de gerar.")
            return
        if not self._image_path:
            QMessageBox.warning(self, "Aviso", "Carregue uma imagem de modelo primeiro.")
            return
        if not self._planilha_path:
            QMessageBox.warning(self, "Aviso", "Selecione uma planilha (.xlsx).")
            return
        if not self._fonte_path:
            QMessageBox.warning(self, "Aviso", "Selecione uma fonte (.ttf).")
            return

        try:
            df = pd.read_excel(self._planilha_path, dtype=str).fillna("")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao ler a planilha: {e}")
            return

        total_rows = len(df)
        if total_rows == 0:
            QMessageBox.warning(self, "Aviso", "A planilha selecionada está vazia.")
            return

        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)

        margem_h, margem_v = 15, 5
        tam_min = 16

        largura_nome = coords_nome[2] - coords_nome[0] - (margem_h * 2)
        altura_nome = coords_nome[3] - coords_nome[1] - (margem_v * 2)
        largura_equipe = coords_equipe[2] - coords_equipe[0] - (margem_h * 2)
        altura_equipe = coords_equipe[3] - coords_equipe[1] - (margem_v * 2)

        dummy = Image.new("RGB", (100, 100))
        ddraw = ImageDraw.Draw(dummy)

        def calcular_fonte(lista_textos, tam_ideal, larg_max, alt_max):
            for t in range(tam_ideal, tam_min - 1, -1):
                f = ImageFont.truetype(self._fonte_path, t)
                if all(
                    (bb[2] - bb[0]) <= larg_max and (bb[3] - bb[1]) <= alt_max
                    for txt in lista_textos if (tx := str(txt).strip().upper())
                    for bb in [ddraw.textbbox((0, 0), tx, font=f)]
                ):
                    return f
            return ImageFont.truetype(self._fonte_path, tam_min)

        fonte_nome = calcular_fonte(df.iloc[:, 0], 40, largura_nome, altura_nome)
        fonte_equipe = calcular_fonte(df.iloc[:, 1], 34, largura_equipe, altura_equipe)

        cx_nome, cy_nome = (coords_nome[0] + coords_nome[2]) / 2.0, (coords_nome[1] + coords_nome[3]) / 2.0
        cx_equipe, cy_equipe = (coords_equipe[0] + coords_equipe[2]) / 2.0, (coords_equipe[1] + coords_equipe[3]) / 2.0

        gerados = 0
        for idx, linha in df.iterrows():
            nome = str(linha.iloc[0]).strip().upper()
            equipe = str(linha.iloc[1]).strip().upper()

            if nome and nome != "NAN":
                img = Image.open(self._image_path).convert("RGB")
                draw = ImageDraw.Draw(img)
                draw.text((cx_nome, cy_nome), nome, font=fonte_nome, fill="black", anchor="mm")
                draw.text((cx_equipe, cy_equipe), equipe, font=fonte_equipe, fill="black", anchor="mm")

                nome_limpo = "".join([c if c.isalnum() else "_" for c in nome])
                caminho = os.path.join(self._saida_dir, f"{nome_limpo}.png")
                
                img.save(caminho, "PNG", optimize=True)
                gerados += 1

            self._progress_bar.setValue(int(((idx + 1) / total_rows) * 100))
            QApplication.processEvents()

        self._progress_bar.setVisible(False)
        QMessageBox.information(self, "Sucesso", f"Processo concluído!\nCrachás gerados: {gerados}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
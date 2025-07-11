from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGridLayout, QApplication,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui  import QPalette, QColor, QFont
from PySide6.QtCore import Qt


class PlotWidget(QWidget):
    """Dark/light-mode dashboard for live IMU values + feature list."""

    # ──────────────────────────────── init ────────────────────────────────
    def __init__(self) -> None:
        super().__init__()

        # -------- palette & base colors first (needed by _card) ------------
        pal  = QApplication.instance().palette()
        dark = pal.color(QPalette.Window).lightness() < 128

        self._bg   = "#1e1e1e" if dark else "#ffffff"
        self._fg   = "#f0f0f0" if dark else "#1f2630"
        self._blue = "#4a9eff" if dark else "#3498db"
        self._warm = "#ff6b6b" if dark else "#e74c3c"
        self._cool = "#4ecdc4" if dark else "#1abc9c"

        self.setStyleSheet(f"background:{self._bg}; color:{self._fg};")

        # ---------------------- layout skeleton ----------------------------
        main = QVBoxLayout(self)
        main.setContentsMargins(30, 30, 30, 30)
        main.setSpacing(25)

        # header (title + feature names later)
        self.header = QLabel("M5StickC Plus – Waiting for features …",
                             alignment=Qt.AlignCenter)
        self.header.setWordWrap(True)
        self.header.setMinimumHeight(60)
        self._style_header()
        self._add_shadow(self.header)
        main.addWidget(self.header, 0, Qt.AlignTop)

        # grid with six live values
        grid = QGridLayout(); grid.setSpacing(20)

        self.acc_x = QLabel(); self.acc_y = QLabel(); self.acc_z = QLabel()
        self.gyr_x = QLabel(); self.gyr_y = QLabel(); self.gyr_z = QLabel()

        grid.addWidget(self._section("ACCELEROMETER"), 0, 0, 1, 3)
        grid.addWidget(self._card(self.acc_x, "warm"), 1, 0)
        grid.addWidget(self._card(self.acc_y, "warm"), 1, 1)
        grid.addWidget(self._card(self.acc_z, "warm"), 1, 2)

        grid.addWidget(self._section("GYROSCOPE"),     2, 0, 1, 3)
        grid.addWidget(self._card(self.gyr_x, "cool"), 3, 0)
        grid.addWidget(self._card(self.gyr_y, "cool"), 3, 1)
        grid.addWidget(self._card(self.gyr_z, "cool"), 3, 2)

        main.addLayout(grid, 1)

    # ────────────────────── public API used by MainWindow ─────────────────
    def add_sample(self, ax:int, ay:int, az:int, gx:int, gy:int, gz:int) -> None:
        self.acc_x.setText(f"{ax:+6d}")
        self.acc_y.setText(f"{ay:+6d}")
        self.acc_z.setText(f"{az:+6d}")
        self.gyr_x.setText(f"{gx:+6d}")
        self.gyr_y.setText(f"{gy:+6d}")
        self.gyr_z.setText(f"{gz:+6d}")

    def show_feature_headers(self, headers:list[str]) -> None:
        if headers:
            self.header.setText("M5StickC Plus – Features:  " + ", ".join(headers))

    # ───────────────────────── helper widgets ─────────────────────────────
    def _style_header(self) -> None:
        self.header.setStyleSheet(f"""
            QLabel {{
                background:rgba(74,158,255,0.15);
                border:2px solid {self._blue};
                border-radius:12px;
                padding:14px;
                font-size:20px;
                font-weight:600;
                color:{self._fg};
                font-family: Arial, Helvetica, sans-serif;
            }}""")

    def _card(self, lbl: QLabel, tone:str) -> QWidget:
        wrap = QWidget()
        lay  = QVBoxLayout(wrap); lay.addWidget(lbl)
        lay.setContentsMargins(0,0,0,0)

        border = self._warm if tone == "warm" else self._cool
        wrap.setStyleSheet(f"""
            QWidget {{
                background:rgba(255,255,255,0.05);
                border:2px solid {border};
                border-radius:10px;
            }}
            QWidget:hover {{
                background:{border};
                color:#ffffff;
            }}""")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Courier New", 18, QFont.Bold))
        lbl.setText("—")
        self._add_shadow(wrap, blur=12, yoff=2)
        return wrap

    def _section(self, text:str) -> QLabel:
        lab = QLabel(text, alignment=Qt.AlignCenter)
        lab.setFont(QFont("Arial", 11, QFont.Bold))
        lab.setStyleSheet("letter-spacing:1px;")
        return lab

    @staticmethod
    def _add_shadow(widget:QWidget, blur:int=15, yoff:int=3) -> None:
        sh = QGraphicsDropShadowEffect(widget)
        sh.setBlurRadius(blur)
        sh.setOffset(0, yoff)
        sh.setColor(QColor(0,0,0,120))
        widget.setGraphicsEffect(sh)
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QApplication
from PySide6.QtCore    import Qt
from PySide6.QtGui     import QPalette

class FeatureWidget(QWidget):
    """Dynamic grid that shows feature headers + latest values."""

    def __init__(self) -> None:
        super().__init__()
        self._grid      = QGridLayout(self)
        self._labels    = []   # value labels
        self._headers   = []   # header strings
        self._setup_palette()

    # ────────────────────────────────────────────────────────────
    def _setup_palette(self) -> None:
        palette       = QApplication.instance().palette()
        self._dark    = palette.color(QPalette.Window).lightness() < 128
        self._txt_col = "#ffffff" if self._dark else "#2c3e50"
        self._bg_col  = "#2b2b2b" if self._dark else "#ffffff"
        self.setStyleSheet(f"background:{self._bg_col}; color:{self._txt_col};")

    # ────────────────────────────────────────────────────────────
    def set_headers(self, headers: list[str]) -> None:
        # clear old grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._labels.clear()
        self._headers = headers

        cols = 3  # nice 3-col grid
        for i, h in enumerate(headers):
            row, col = divmod(i, cols)
            head = QLabel(h)
            val  = QLabel("—")
            head.setAlignment(Qt.AlignCenter)
            val .setAlignment(Qt.AlignCenter)
            head.setStyleSheet("font-weight:bold;")
            self._grid.addWidget(head, row*2,   col)
            self._grid.addWidget(val,  row*2+1, col)
            self._labels.append(val)

    def update_values(self, values: list[float]) -> None:
        for lbl, v in zip(self._labels, values):
            lbl.setText(f"{v: .3f}")
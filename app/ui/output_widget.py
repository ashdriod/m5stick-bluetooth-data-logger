from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PySide6.QtGui     import QPalette, QFont
from PySide6.QtCore    import Qt

class OutputWidget(QWidget):
    """Simple placeholder screen showing Tiny-ML output."""

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignCenter); lay.setSpacing(40)

        self.label = QLabel("Connect the Device First", alignment=Qt.AlignCenter)
        self.label.setFont(QFont("Arial", 40, QFont.Bold))

        self.btn_back = QPushButton("◀ Back to Input")

        lay.addWidget(self.label)
        lay.addWidget(self.btn_back, 0, Qt.AlignCenter)

        pal  = QApplication.instance().palette()
        dark = pal.color(QPalette.Window).lightness() < 128
        fg   = "#f0f0f0" if dark else "#1f2630"
        self.label.setStyleSheet(f"color:{fg};")


    def update_output(self, text: str) -> None:
        self.label.setText(text)    
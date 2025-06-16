from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
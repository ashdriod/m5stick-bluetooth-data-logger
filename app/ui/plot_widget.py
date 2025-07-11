from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QApplication
from PySide6.QtCore    import Qt
from PySide6.QtGui     import QPalette

class PlotWidget(QWidget):
    """Dark/light-mode compatible display for live IMU values + feature list."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── big blue header (title + feature list)
        self.header = QLabel("M5StickC Plus – Live IMU Data", alignment=Qt.AlignCenter)
        self.header.setWordWrap(True)
        layout.addWidget(self.header)

        # ── grid for the six raw values
        grid = QGridLayout(); grid.setSpacing(15)
        self.acc_x = QLabel("AccX: 0"); self.acc_y = QLabel("AccY: 0"); self.acc_z = QLabel("AccZ: 0")
        self.gyr_x = QLabel("GyrX: 0"); self.gyr_y = QLabel("GyrY: 0"); self.gyr_z = QLabel("GyrZ: 0")

        grid.addWidget(QLabel("ACC"), 0, 0, Qt.AlignCenter)
        grid.addWidget(self.acc_x,    1, 0)
        grid.addWidget(self.acc_y,    1, 1)
        grid.addWidget(self.acc_z,    1, 2)

        grid.addWidget(QLabel("GYR"), 2, 0, Qt.AlignCenter)
        grid.addWidget(self.gyr_x,    3, 0)
        grid.addWidget(self.gyr_y,    3, 1)
        grid.addWidget(self.gyr_z,    3, 2)

        layout.addLayout(grid)
        self._apply_styling()

    # ────────────────────────────────────────────────────────────
    def _apply_styling(self) -> None:
        pal = QApplication.instance().palette()
        dark = pal.color(QPalette.Window).lightness() < 128

        bg      = "#2b2b2b" if dark else "#ffffff"
        txt     = "#ffffff" if dark else "#2c3e50"
        accent  = "#4a9eff" if dark else "#3498db"

        self.setStyleSheet(f"background:{bg}; color:{txt};")
        self.header.setStyleSheet(f"""
            QLabel {{
                background:{accent};
                color:white;
                font-size:18px;
                font-weight:bold;
                border-radius:8px;
                padding:10px;
            }}""")

        for lbl in (self.acc_x, self.acc_y, self.acc_z,
                    self.gyr_x, self.gyr_y, self.gyr_z):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-family:'Courier New'; font-size:16px;")

    # ────────────────────────────────────────────────────────────
    def add_sample(self, ax:int, ay:int, az:int, gx:int, gy:int, gz:int) -> None:
        self.acc_x.setText(f"X: {ax:6d}")
        self.acc_y.setText(f"Y: {ay:6d}")
        self.acc_z.setText(f"Z: {az:6d}")
        self.gyr_x.setText(f"X: {gx:6d}")
        self.gyr_y.setText(f"Y: {gy:6d}")
        self.gyr_z.setText(f"Z: {gz:6d}")

    # ────────────────────────────────────────────────────────────
    def show_feature_headers(self, headers: list[str]) -> None:
        if not headers: return
        joined = ", ".join(headers)
        self.header.setText(f"M5StickC Plus – Features:  {joined}")
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg

class PlotWidget(QWidget):
    """Real-time IMU plot (Accel X/Y/Z)."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        self.plot = pg.PlotWidget(title="Live IMU Data")
        self.plot.addLegend()
        self.curves = {
            axis: self.plot.plot(pen=pg.mkPen(width=2), name=axis)
            for axis in ("X", "Y", "Z")
        }
        layout.addWidget(self.plot)

    def update(self, x, y, z) -> None:
        # TODO: push new data points to curves
        pass

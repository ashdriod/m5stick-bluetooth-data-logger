# app/ui/main_window.py
from __future__ import annotations

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QMessageBox
)

from app.services.bluetooth import DeviceScanner, BLEClient, BLEDeviceInfo
from app.services.recorder  import CSVRecorder
from app.ui.plot_widget     import PlotWidget


class MainWindow(QMainWindow):
    """GUI for scanning, connecting, plotting and recording."""

    # ------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("M5Stick-BLE Data Logger")
        self.resize(750, 520)

        # ── widgets
        self.status        = QLabel("Idle", alignment=Qt.AlignLeft)
        self.device_list   = QListWidget()

        self.btn_scan      = QPushButton("Scan")
        self.btn_connect   = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")     # NEW
        self.btn_start     = QPushButton("Start Recording")
        self.btn_stop      = QPushButton("Stop Recording")

        self.plot          = PlotWidget()

        # ── layout
        side = QVBoxLayout()
        for w in (
            self.device_list, self.btn_scan, self.btn_connect,
            self.btn_disconnect, self.btn_start, self.btn_stop, self.status
        ):
            side.addWidget(w)

        container = QWidget()
        main = QHBoxLayout(container)
        main.addWidget(self.plot, 3)
        main.addLayout(side, 1)
        self.setCentralWidget(container)

        # ── state
        self._scanner: DeviceScanner | None = None
        self._client : BLEClient     | None = None
        self._rec    : CSVRecorder   | None = None

        # ── initial button states
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_disconnect.setEnabled(False)

        # ── signals
        self.btn_scan.clicked.connect(self.scan_devices)
        self.btn_connect.clicked.connect(self.connect_selected)
        self.btn_disconnect.clicked.connect(self.force_disconnect)   # NEW
        self.btn_start.clicked.connect(self.start_rec)
        self.btn_stop.clicked.connect(self.stop_rec)

    # ============================================================
    # Scanning ----------------------------------------------------
    def scan_devices(self) -> None:
        self.device_list.clear()
        self.status.setText("Scanning …")
        self.btn_scan.setEnabled(False)

        self._scanner = DeviceScanner(timeout=5.0)
        self._scanner.device_found.connect(self._add_device)
        self._scanner.scan_finished.connect(self._scan_done)
        self._scanner.start()

    def _add_device(self, info: BLEDeviceInfo) -> None:
        text = f"{info.name} [{info.address}]  RSSI:{info.rssi}"
        self.device_list.addItem(text)

    def _scan_done(self) -> None:
        self.status.setText("Scan complete."
                            if self.device_list.count() else "No devices found.")
        self.btn_scan.setEnabled(True)

    # ============================================================
    # Connection --------------------------------------------------
    def connect_selected(self) -> None:
        if self._client:
            QMessageBox.information(self, "Already connected", "Disconnect first.")
            return

        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No selection", "Pick a device first.")
            return

        address = item.text().split("[")[1].split("]")[0]
        self.status.setText(f"Connecting to {address} …")

        self._client = BLEClient(address)
        self._client.connected.connect(lambda: self._on_connected(address))
        self._client.disconnected.connect(self._on_disconnected)
        self._client.packet_ready.connect(self._handle_packet)
        self._client.start()

    def force_disconnect(self) -> None:                       # NEW
        if self._client:
            self.status.setText("Disconnecting …")
            self._client.request_disconnect()  # async flag inside thread

    def _on_connected(self, addr: str) -> None:
        self.status.setText(f"Connected to {addr}")
        self.btn_start.setEnabled(True)
        self.btn_disconnect.setEnabled(True)

    def _on_disconnected(self, reason: str) -> None:
        self.status.setText(f"Disconnected: {reason}")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_disconnect.setEnabled(False)
        self._client = None
        if self._rec:
            self.stop_rec()

    # ============================================================
    # Recording & plotting ---------------------------------------
    def start_rec(self) -> None:
        self._rec = CSVRecorder(prefix="m5session")
        self.status.setText(f"Recording → {self._rec.path.name}")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_rec(self) -> None:
        if not self._rec:
            return
        rec, self._rec = self._rec, None
        rec.close()
        QMessageBox.information(self, "Saved", f"Data written to {rec.path}")
        self.status.setText("Recording stopped.")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    # ----- incoming BLE packet
    def _handle_packet(self, rows: list[tuple]) -> None:
        _ts, ax, ay, az, gx, gy, gz = rows[-1]
        self.plot.add_sample(ax, ay, az, gx, gy, gz)
        if self._rec and not self._rec.closed:
            self._rec.add_rows(rows)
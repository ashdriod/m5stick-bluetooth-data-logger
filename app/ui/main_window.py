from __future__ import annotations
import time

from PySide6.QtCore    import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QMessageBox
)

from app.services.bluetooth import DeviceScanner, BLEClient, BLEDeviceInfo
from app.services.recorder  import CSVRecorder
from app.ui.plot_widget     import PlotWidget


class MainWindow(QMainWindow):
    """Scan, connect, view IMU + feature headers, record both CSVs."""

    # ------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("M5Stick-BLE Data Logger")
        self.resize(800, 540)

        # ── controls column
        self.status         = QLabel("Idle")
        self.device_list    = QListWidget()
        self.btn_scan       = QPushButton("Scan")
        self.btn_connect    = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_start      = QPushButton("Start Recording")
        self.btn_stop       = QPushButton("Stop Recording")

        controls = QVBoxLayout()
        for w in (self.device_list, self.btn_scan, self.btn_connect,
                  self.btn_disconnect, self.btn_start, self.btn_stop, self.status):
            controls.addWidget(w)
        ctrl_box = QWidget(); ctrl_box.setLayout(controls)

        # ── main plot
        self.plot = PlotWidget()

        # overall layout
        root = QWidget(); self.setCentralWidget(root)
        h    = QHBoxLayout(root)
        h.addWidget(self.plot,  3)
        h.addWidget(ctrl_box,   1)

        # ── state
        self._scanner        : DeviceScanner | None = None
        self._client         : BLEClient     | None = None
        self._raw_rec        : CSVRecorder   | None = None
        self._feat_rec       : CSVRecorder   | None = None
        self._feat_headers   : list[str]     | None = None
        self._recording      : bool          = False

        # button states
        self.btn_stop.setEnabled(False)
        self.btn_disconnect.setEnabled(False)

        # signals
        self.btn_scan      .clicked.connect(self.scan_devices)
        self.btn_connect   .clicked.connect(self.connect_selected)
        self.btn_disconnect.clicked.connect(self.force_disconnect)
        self.btn_start     .clicked.connect(self.start_rec)
        self.btn_stop      .clicked.connect(self.stop_rec)

    # ============================================================
    # Scan
    def scan_devices(self) -> None:
        self.device_list.clear()
        self.status.setText("Scanning…"); self.btn_scan.setEnabled(False)
        self._scanner = DeviceScanner(timeout=5)
        self._scanner.device_found .connect(self._add_device)
        self._scanner.scan_finished.connect(lambda: (self.status.setText(
            "Done" if self.device_list.count() else "No devices"), self.btn_scan.setEnabled(True)))
        self._scanner.start()

    def _add_device(self, info: BLEDeviceInfo) -> None:
        self.device_list.addItem(f"{info.name} [{info.address}]  RSSI:{info.rssi}")

    # ============================================================
    # Connect / Disconnect
    def connect_selected(self) -> None:
        if self._client:
            QMessageBox.information(self, "Already connected", "Disconnect first."); return
        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No selection", "Pick a device."); return
        addr = item.text().split("[")[1].split("]")[0]
        self.status.setText(f"Connecting to {addr}…")

        self._client = BLEClient(addr)
        self._client.connected      .connect(lambda: self._on_connected(addr))
        self._client.disconnected   .connect(self._on_disconnected)
        self._client.packet_ready   .connect(self._handle_raw)
        self._client.feature_header .connect(self._handle_header)
        self._client.feature_values .connect(self._handle_values)
        self._client.start()

    def force_disconnect(self) -> None:
        if self._client:
            self.status.setText("Disconnecting…")
            self._client.request_disconnect()

    def _on_connected(self, addr:str) -> None:
        self.status.setText(f"Connected to {addr}")
        self.btn_disconnect.setEnabled(True)
        self.btn_start     .setEnabled(True)

    def _on_disconnected(self, reason:str) -> None:
        self.status.setText(f"Disconnected: {reason}")
        self.btn_disconnect.setEnabled(False)
        self.btn_start     .setEnabled(False)
        self.btn_stop      .setEnabled(False)
        self._client = None
        self.stop_rec()    # ensures files are closed

    # ============================================================
    # Recording
    def start_rec(self) -> None:
        self._raw_rec   = CSVRecorder(prefix="raw")
        self._recording = True

        self.btn_start.setEnabled(False)
        self.btn_stop .setEnabled(True)
        self.status.setText("Recording…")

    def stop_rec(self) -> None:
        self._recording = False
        for r in (self._raw_rec, self._feat_rec):
            if r: r.close()
        self._raw_rec = self._feat_rec = None
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)

    # ============================================================
    # Data callbacks
    def _handle_raw(self, rows:list[tuple]) -> None:
        ts, ax, ay, az, gx, gy, gz = rows[-1]
        self.plot.add_sample(ax, ay, az, gx, gy, gz)
        if self._recording and self._raw_rec:
            self._raw_rec.add_rows(rows)

    def _handle_header(self, headers: list[str]) -> None:
        self._feat_headers = headers
        self.plot.show_feature_headers(headers)

        # Create feature CSV immediately (if not yet done)
        if self._feat_rec is None:
            cols = ["timestamp_ms", *headers]
            self._feat_rec = CSVRecorder(prefix="features", headers=cols)

    def _handle_values(self, vals:list[float]) -> None:
        if self._recording and self._feat_rec:
            self._feat_rec.add_rows([(int(time.time()*1000), *vals)])
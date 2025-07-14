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
from app.ui.output_widget   import OutputWidget


class MainWindow(QMainWindow):
    """Input-mode: plot + logging  •  Output-mode: prediction screen."""

    # ------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("M5Stick-BLE Data Logger")
        self.resize(820, 560)

        # ────────── INPUT widgets ──────────────────────────────
        self.status         = QLabel("Idle")
        self.device_list    = QListWidget()
        self.btn_scan       = QPushButton("Scan")
        self.btn_connect    = QPushButton("Connect")
        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_start      = QPushButton("Start Recording")
        self.btn_stop       = QPushButton("Stop Recording")
        self.btn_show_out   = QPushButton("▶  Show Output")

        # segment controls
        self._segment = 1
        self.lbl_seg  = QLabel("Segment: 1", alignment=Qt.AlignCenter)
        self.btn_seg_p = QPushButton("＋"); self.btn_seg_p.setFixedWidth(32)
        self.btn_seg_m = QPushButton("－"); self.btn_seg_m.setFixedWidth(32)
        seg_row = QHBoxLayout()
        seg_row.addWidget(self.btn_seg_m); seg_row.addWidget(self.lbl_seg, 1); seg_row.addWidget(self.btn_seg_p)
        seg_wrap = QWidget(); seg_wrap.setLayout(seg_row)

        vbox = QVBoxLayout()
        for w in (self.device_list, self.btn_scan, self.btn_connect,
                  self.btn_disconnect, seg_wrap,
                  self.btn_start, self.btn_stop,
                  self.status, self.btn_show_out):
            vbox.addWidget(w)
        ctrl_box = QWidget(); ctrl_box.setLayout(vbox)

        self.plot = PlotWidget()
        self._input_root = QWidget()
        h = QHBoxLayout(self._input_root)
        h.addWidget(self.plot, 3); h.addWidget(ctrl_box, 1)

        # ────────── OUTPUT widget ──────────────────────────────
        self._output_widget = OutputWidget()

        # stacked container
        self._stack = QWidget(); self.setCentralWidget(self._stack)
        stack = QVBoxLayout(self._stack); stack.setContentsMargins(0, 0, 0, 0)
        stack.addWidget(self._input_root)      # index 0
        stack.addWidget(self._output_widget)   # index 1
        self._output_widget.hide()
        self._output_mode = False

        # ────────── state ─────────────────────────────────────
        self._scanner      : DeviceScanner | None = None
        self._client       : BLEClient     | None = None
        self._raw_rec      : CSVRecorder   | None = None
        self._feat_rec     : CSVRecorder   | None = None
        self._feat_headers : list[str]     | None = None
        self._recording    = False

        self.btn_disconnect.setEnabled(False)
        self.btn_stop.setEnabled(False)

        # signals
        self.btn_scan.clicked.connect(self.scan_devices)
        self.btn_connect.clicked.connect(self.connect_selected)
        self.btn_disconnect.clicked.connect(self.force_disconnect)
        self.btn_start.clicked.connect(self.start_rec)
        self.btn_stop.clicked.connect(self.stop_rec)
        self.btn_seg_p.clicked.connect(lambda: self._change_segment(1))
        self.btn_seg_m.clicked.connect(lambda: self._change_segment(-1))
        self.btn_show_out.clicked.connect(self._show_output_mode)
        self._output_widget.btn_back.clicked.connect(self._show_input_mode)

    # ============================================================
    # Mode toggle
    def _show_output_mode(self):
        if self._output_mode:
            return
        self._output_mode = True
        self._input_root.hide(); self._output_widget.show()

    def _show_input_mode(self):
        if not self._output_mode:
            return
        self._output_mode = False
        self._output_widget.hide(); self._input_root.show()

    # ============================================================
    # Segment
    def _change_segment(self, d:int):
        self._segment = max(1, self._segment + d)
        self.lbl_seg.setText(f"Segment: {self._segment}")

    # ============================================================
    # Scanning
    def scan_devices(self):
        if self._client:   # already connected → ignore
            return
        self.device_list.clear(); self.btn_scan.setEnabled(False)
        self.status.setText("Scanning…")
        self._scanner = DeviceScanner(timeout=5)
        self._scanner.device_found.connect(
            lambda d: self.device_list.addItem(f"{d.name} [{d.address}]  RSSI:{d.rssi}"))
        self._scanner.scan_finished.connect(
            lambda: (self.status.setText("Done"), self.btn_scan.setEnabled(True)))
        self._scanner.start()

    # ============================================================
    # Connect / disconnect
    def connect_selected(self):
        if self._client:
            QMessageBox.information(self, "Already connected", "Disconnect first.")
            return
        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No selection", "Pick a device.")
            return
        addr = item.text().split("[")[1].split("]")[0]

        self.status.setText(f"Connecting to {addr}…")
        self._client = BLEClient(addr)
        self._client.connected.connect(self._on_connected)
        self._client.disconnected.connect(self._on_disconnected)
        self._client.packet_ready.connect(self._handle_raw)
        self._client.feature_header.connect(self._handle_header)
        self._client.feature_values.connect(self._handle_values)
        self._client.start()

    def _on_connected(self):
        self.status.setText("Connected")
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def _on_disconnected(self, reason:str):
        self.status.setText(f"Disc: {reason}")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.stop_rec()
        self._client = None

    def force_disconnect(self):
        if self._client:
            self._client.request_disconnect()

    # ============================================================
    # Recording
    def start_rec(self):
        self._raw_rec = CSVRecorder(
            prefix="raw",
            headers=["segment","timestamp_ms",
                     "acc_x","acc_y","acc_z","gyro_x","gyro_y","gyro_z"])

        # create feature file ONLY while recording
        if self._feat_headers is not None:
            self._feat_rec = CSVRecorder(
                prefix="features",
                headers=["segment","timestamp_ms", *self._feat_headers])

        self._recording = True
        self.status.setText("Recording…")
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)

    def stop_rec(self):
        self._recording = False
        for r in (self._raw_rec, self._feat_rec):
            if r: r.close()
        self._raw_rec = self._feat_rec = None
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)

    # ============================================================
    # Data callbacks
    def _handle_raw(self, rows:list[tuple]):
        _, ax, ay, az, gx, gy, gz = rows[-1]
        if not self._output_mode:
            self.plot.add_sample(ax, ay, az, gx, gy, gz)
        if self._recording and self._raw_rec:
            self._raw_rec.add_rows_with_prefix(self._segment, rows)

    def _handle_header(self, headers:list[str]):
        self._feat_headers = headers
        self.plot.show_feature_headers(headers)

        # create feature file only if we're actively recording
        if self._recording and self._feat_rec is None:
            cols = ["segment","timestamp_ms", *headers]
            self._feat_rec = CSVRecorder(prefix="features", headers=cols)

    def _handle_values(self, vals:list[float]):
        if self._recording and self._feat_rec:
            ts = int(time.time()*1000)
            self._feat_rec.add_rows_with_prefix(self._segment, [(ts, *vals)])
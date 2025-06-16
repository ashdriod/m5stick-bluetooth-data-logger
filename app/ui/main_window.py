"""Main GUI window with device list, control buttons and live plot."""

from __future__ import annotations
from pathlib import Path
import csv
import datetime

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QLabel, QFileDialog, QMainWindow, QMessageBox
)
import pyqtgraph as pg

from app.services.bluetooth import ScanWorker, BLEStreamClient


class MainWindow(QMainWindow):
    """Main application window."""

    NOTIFY_UUID = "0000FFE1-0000-1000-8000-00805F9B34FB"  # example UUID; replace with your characteristic

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("M5Stick BLE Logger")
        self.resize(800, 500)

        # UI Elements
        self.device_list = QListWidget()
        self.status_label = QLabel("Ready")

        self.btn_scan = QPushButton("Scan")
        self.btn_connect = QPushButton("Connect")
        self.btn_start = QPushButton("Start Recording")
        self.btn_stop = QPushButton("Stop Recording")

        # Plot
        self.plot = pg.PlotWidget(title="Accel X/Y/Z")
        self.plot.addLegend()
        self.curves = {
            axis: self.plot.plot(pen=pg.mkPen(width=2), name=axis)
            for axis in ("X", "Y", "Z")
        }
        self.x_data: list[int] = []
        self.y_data = {axis: [] for axis in ("X", "Y", "Z")}
        self._ts0 = datetime.datetime.now()

        # Layouts
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.device_list)
        left_layout.addWidget(self.btn_scan)
        left_layout.addWidget(self.btn_connect)
        left_layout.addStretch()
        left_layout.addWidget(self.status_label)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.plot)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        right_layout.addLayout(btn_row)

        container = QWidget()
        hbox = QHBoxLayout(container)
        hbox.addLayout(left_layout, 2)
        hbox.addLayout(right_layout, 5)
        self.setCentralWidget(container)

        # Connections
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_connect.clicked.connect(self.connect_device)
        self.btn_start.clicked.connect(self.start_recording)
        self.btn_stop.clicked.connect(self.stop_recording)

        # Threads / workers holders
        self._scan_thread: QThread | None = None
        self._ble_client: BLEStreamClient | None = None
        self._client_thread: QThread | None = None

        # Recording state
        self._csv_writer: csv.writer | None = None
        self._csv_file = None

    # ---------- Scan / Connect ----------
    @Slot()
    def start_scan(self):
        if self._scan_thread and self._scan_thread.isRunning():
            return  # already scanning
        self.device_list.clear()
        self.status_label.setText("Scanning…")

        self._scan_thread = QThread()
        worker = ScanWorker(timeout=5.0)
        worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(worker.run)
        worker.device_found.connect(self.add_device)
        worker.finished.connect(self._scan_thread.quit)
        worker.finished.connect(worker.deleteLater)
        self._scan_thread.finished.connect(self.scan_finished)
        self._scan_thread.start()

    @Slot(str, str)
    def add_device(self, name: str, address: str):
        self.device_list.addItem(f"{name} | {address}")

    @Slot()
    def scan_finished(self):
        self.status_label.setText("Scan finished")

    @Slot()
    def connect_device(self):
        item = self.device_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No device", "Please select a device first")
            return
        address = item.text().split("|")[-1].strip()
        self.status_label.setText(f"Connecting to {address}…")

        self._client_thread = QThread()
        self._ble_client = BLEStreamClient(address, self.NOTIFY_UUID)
        self._ble_client.moveToThread(self._client_thread)
        self._client_thread.started.connect(self._ble_client.start)

        # Signals
        self._ble_client.connected.connect(lambda: self.status_label.setText("Connected"))
        self._ble_client.disconnected.connect(lambda: self.status_label.setText("Disconnected"))
        self._ble_client.error.connect(lambda e: QMessageBox.critical(self, "BLE Error", e))
        self._ble_client.data_received.connect(self.handle_payload)

        self._client_thread.start()

    # ---------- Data / Plot / CSV ----------
    @Slot(bytes)
    def handle_payload(self, payload: bytes):
        # payload is 6*int16 = 12 bytes little‑endian
        if len(payload) != 12:
            return
        acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z = int.from_bytes(payload[0:2], "little", signed=True), \
                                                      int.from_bytes(payload[2:4], "little", signed=True), \
                                                      int.from_bytes(payload[4:6], "little", signed=True), \
                                                      int.from_bytes(payload[6:8], "little", signed=True), \
                                                      int.from_bytes(payload[8:10], "little", signed=True), \
                                                      int.from_bytes(payload[10:12], "little", signed=True)
        t_ms = int((datetime.datetime.now() - self._ts0).total_seconds() * 1000)
        self.x_data.append(t_ms)
        for axis, v in zip(("X", "Y", "Z"), (acc_x, acc_y, acc_z)):
            self.y_data[axis].append(v)
            self.curves[axis].setData(self.x_data, self.y_data[axis])

        if self._csv_writer:
            self._csv_writer.writerow([t_ms, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z])

    # ---------- Recording ----------
    @Slot()
    def start_recording(self):
        if self._csv_writer:
            return  # already recording
        Path("data").mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_name = f"session_{ts}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", str(Path("data") / default_name), "CSV (*.csv)")
        if not path:
            return
        self._csv_file = open(path, "w", newline="")
        self._csv_writer = csv.writer(self._csv_file)
        self._csv_writer.writerow(["timestamp_ms", "acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"])
        self.status_label.setText(f"Recording → {Path(path).name}")

    @Slot()
    def stop_recording(self):
        if self._csv_file:
            self._csv_file.close()
            self._csv_writer = None
            self._csv_file = None
            self.status_label.setText("Recording stopped")

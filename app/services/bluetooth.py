"""
Bluetooth helper – now streams BOTH raw IMU packets and
feature vectors with dynamic headers.

Requires: bleak (≥0.22), PySide6
"""
from __future__ import annotations

import asyncio, struct, time
from dataclasses import dataclass
from typing import List

from bleak import BleakClient, BleakScanner, exc
from PySide6.QtCore import QObject, QThread, Signal, QMetaObject, Qt

# ────────────────────────────────────────────────────────────────
SERVICE_UUID  = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
STREAM_UUID   = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"   # raw IMU notify
FEATURE_UUID  = "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"   # feature notify

@dataclass
class BLEDeviceInfo:
    address: str
    name: str
    rssi: int

# ═════════════════════════════════════════════════ Scanner ══════
class DeviceScanner(QObject):
    device_found  = Signal(object)      # BLEDeviceInfo
    scan_finished = Signal()

    def __init__(self, timeout: float = 5.0):
        super().__init__()
        self._timeout = timeout
        self._thread  = QThread(self)

    # ------------------------------------------------------------
    def start(self) -> None:
        self.moveToThread(self._thread)
        self._thread.started.connect(self._scan_async)
        self._thread.start()

    # ------------------------------------------------------------
    def _scan_async(self) -> None:
        async def do_scan():
            devices = await BleakScanner.discover(timeout=self._timeout)
            for d in devices:
                self.device_found.emit(
                    BLEDeviceInfo(
                        address=d.address,
                        name=d.name or "Unnamed",
                        rssi=getattr(d, "rssi", 0),
                    )
                )
            self.scan_finished.emit()

        asyncio.run(do_scan())
        QMetaObject.invokeMethod(self._thread, "quit", Qt.QueuedConnection)

# ═════════════════════════════════════════════════ Client ═══════
class BLEClient(QObject):
    """Handles a single BLE link in its own QThread / asyncio loop."""

    packet_ready       = Signal(list)          # list[tuple(ts, ax, ay, az, gx, gy, gz)]
    feature_header     = Signal(list)          # list[str]
    feature_values     = Signal(list)          # list[float]
    connected          = Signal()
    disconnected       = Signal(str)

    # ------------------------------------------------------------
    def __init__(self, address: str):
        super().__init__()
        self._addr         = address
        self._loop         = asyncio.new_event_loop()
        self._bleak: BleakClient | None = None
        self._should_stop  = False

        self._thread = QThread(self)
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run_loop)
        self._thread.finished.connect(self._loop.stop)

        self._feat_headers: list[str] | None = None

    # ------------------------------------------------------------
    def start(self) -> None:
        self._thread.start()

    def request_disconnect(self) -> None:
        self._should_stop = True
        if self._bleak and self._bleak.is_connected:
            asyncio.run_coroutine_threadsafe(self._bleak.disconnect(),
                                             self._loop)

    # ------------------------------------------------------------
    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_main())

    async def _async_main(self) -> None:
        try:
            self._bleak = BleakClient(
                self._addr, disconnected_callback=self._on_remote_disconnect
            )
            await self._bleak.connect(timeout=10.0)
            self.connected.emit()

            await self._bleak.start_notify(STREAM_UUID,  self._raw_cb)
            await self._bleak.start_notify(FEATURE_UUID, self._feat_cb)

            while not self._should_stop and self._bleak.is_connected:
                await asyncio.sleep(0.1)

            if self._bleak.is_connected:
                await self._bleak.stop_notify(STREAM_UUID)
                await self._bleak.stop_notify(FEATURE_UUID)
                await self._bleak.disconnect()

            self.disconnected.emit("Central requested")

        except exc.BleakError as e:
            self.disconnected.emit(str(e))
        finally:
            QMetaObject.invokeMethod(self._thread, "quit", Qt.QueuedConnection)

    # ------------------------------------------------------------
    def _raw_cb(self, _hdl: int, data: bytearray) -> None:
        if len(data) != 120:                 # 60 int16
            return
        rows, ts_ms = [], int(time.time() * 1000)
        for ax, ay, az, gx, gy, gz in struct.iter_unpack("<hhhhhh", data):
            rows.append((ts_ms, ax, ay, az, gx, gy, gz))
        self.packet_ready.emit(rows)

    def _feat_cb(self, _hdl: int, data: bytearray) -> None:
        line = data.decode(errors="ignore").strip()
        if not line:
            return
        # First packet after (re)connect contains headers
        if self._feat_headers is None:
            self._feat_headers = [h.strip() for h in line.split(',')]
            self.feature_header.emit(self._feat_headers)
        else:
            try:
                values = [float(v) for v in line.split(',')]
                self.feature_values.emit(values)
            except ValueError:
                pass  # corrupted packet – ignore

    def _on_remote_disconnect(self, _client) -> None:
        self._should_stop = True
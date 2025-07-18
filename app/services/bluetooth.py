"""
Bluetooth helper – streams raw IMU packets, feature vectors
(with dynamic headers) AND Tiny-ML predictions.

Requires: bleak ≥ 0.22,  PySide6
"""
from __future__ import annotations

import asyncio, struct, time
from dataclasses import dataclass
from typing import List

from bleak import BleakClient, BleakScanner, exc
from PySide6.QtCore import QObject, QThread, Signal, QMetaObject, Qt


SERVICE_UUID  = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
STREAM_UUID   = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
FEATURE_UUID  = "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"  
PRED_UUID     = "6E400005-B5A3-F393-E0A9-E50E24DCCA9E" 

@dataclass
class BLEDeviceInfo:
    address: str
    name: str
    rssi: int


class DeviceScanner(QObject):
    device_found  = Signal(object)   # BLEDeviceInfo
    scan_finished = Signal()

    def __init__(self, timeout: float = 5.0):
        super().__init__()
        self._timeout = timeout
        self._thread  = QThread(self)

    def start(self) -> None:
        self.moveToThread(self._thread)
        self._thread.started.connect(self._scan_async)
        self._thread.start()

    
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


class BLEClient(QObject):
    """
    Handles a single BLE connection in its own asyncio loop.
    Emits:
      • packet_ready       (list[tuple])   raw 10×6 IMU rows
      • feature_header     (list[str])     first feature CSV header
      • feature_values     (list[float])   subsequent feature rows
      • prediction_ready   (str)           "1", "2", etc.
      • connected() / disconnected(reason)
    """

    packet_ready     = Signal(list)
    feature_header   = Signal(list)
    feature_values   = Signal(list)
    prediction_ready = Signal(str)

    connected        = Signal()
    disconnected     = Signal(str)

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

    
    def start(self) -> None:
        self._thread.start()

    def request_disconnect(self) -> None:
        self._should_stop = True
        if self._bleak and self._bleak.is_connected:
            asyncio.run_coroutine_threadsafe(self._bleak.disconnect(),
                                             self._loop)

   
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

            # Get list of available characteristics on the device
            services = await self._bleak.get_services()
            char_uuids = {char.uuid.lower() for service in services for char in service.characteristics}

            # Optional notify setup
            if STREAM_UUID.lower() in char_uuids:
                await self._bleak.start_notify(STREAM_UUID, self._raw_cb)
            else:
                print("⚠️ STREAM_UUID not found – skipping raw data.")

            if FEATURE_UUID.lower() in char_uuids:
                await self._bleak.start_notify(FEATURE_UUID, self._feat_cb)
            else:
                print("⚠️ FEATURE_UUID not found – skipping feature data.")

            if PRED_UUID.lower() in char_uuids:
                await self._bleak.start_notify(PRED_UUID, self._pred_cb)
            else:
                print("⚠️ PRED_UUID not found – skipping prediction updates.")

            while not self._should_stop and self._bleak.is_connected:
                await asyncio.sleep(0.1)

         
            if self._bleak.is_connected:
                if STREAM_UUID.lower() in char_uuids:
                    await self._bleak.stop_notify(STREAM_UUID)
                if FEATURE_UUID.lower() in char_uuids:
                    await self._bleak.stop_notify(FEATURE_UUID)
                if PRED_UUID.lower() in char_uuids:
                    await self._bleak.stop_notify(PRED_UUID)

                await self._bleak.disconnect()

            self.disconnected.emit("Central requested")

        except exc.BleakError as e:
            self.disconnected.emit(str(e))
        finally:
            QMetaObject.invokeMethod(self._thread, "quit", Qt.QueuedConnection)

    
    def _raw_cb(self, _handle: int, data: bytearray) -> None:
        if len(data) != 120:     # 60 int16 values
            return
        ts_ms = int(time.time() * 1000)
        rows  = [ (ts_ms, *vals)
                  for vals in struct.iter_unpack("<hhhhhh", data) ]
        self.packet_ready.emit(rows)

    def _feat_cb(self, _handle: int, data: bytearray) -> None:
        line = data.decode(errors="ignore").strip()
        if not line:
            return
        if self._feat_headers is None:
            # first message = header
            self._feat_headers = [h.strip() for h in line.split(',')]
            self.feature_header.emit(self._feat_headers)
        else:
            try:
                values = [float(v) for v in line.split(',')]
                self.feature_values.emit(values)
            except ValueError:
                pass  # malformed CSV row – ignore

    def _pred_cb(self, _handle: int, data: bytearray) -> None:
        try:
            msg = data.decode().strip()          # e.g. "PREDICT:2"
            if msg.startswith("PREDICT:"):
                label = msg.split(":", 1)[1]     # "2"
                self.prediction_ready.emit(label)
        except UnicodeDecodeError:
            pass


    def _on_remote_disconnect(self, _client) -> None:
        self._should_stop = True   # make loop exit
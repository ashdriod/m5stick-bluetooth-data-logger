
from __future__ import annotations
import asyncio
from typing import List
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from bleak import BleakScanner, BleakClient


@dataclass
class BLEDeviceInfo:
    name: str
    address: str


class ScanWorker(QObject):
    """Run BLE scan in a separate thread (Qt‑friendly)."""

    device_found = Signal(str, str)  # name, address
    finished = Signal()

    def __init__(self, timeout: float = 4.0) -> None:
        super().__init__()
        self._timeout = timeout

    def run(self) -> None:  # slot for QThread.start()
        try:
            devices = asyncio.run(BleakScanner.discover(timeout=self._timeout))
            for dev in devices:
                self.device_found.emit(dev.name or "<unknown>", dev.address)
        finally:
            self.finished.emit()


class BLEStreamClient(QObject):
    """Handles connection & notifications in its own asyncio loop."""

    data_received = Signal(bytes)  # raw payload
    connected = Signal()
    disconnected = Signal()
    error = Signal(str)

    def __init__(self, address: str, notify_char: str):
        super().__init__()
        self.address = address
        self.notify_char = notify_char  # UUID of notification characteristic
        self.client: BleakClient | None = None

    async def _notification_handler(self, _sender: int, data: bytes):
        self.data_received.emit(data)

    async def _run(self):
        try:
            self.client = BleakClient(self.address)
            await self.client.connect(timeout=10.0)
            self.connected.emit()
            await self.client.start_notify(self.notify_char, self._notification_handler)
            # keep running until disconnected externally
            while await self.client.is_connected():
                await asyncio.sleep(0.1)
        except Exception as exc:  # noqa: BLE exceptions
            self.error.emit(str(exc))
        finally:
            self.disconnected.emit()

    def start(self):
        asyncio.run(self._run())

    async def stop_async(self):
        if self.client and await self.client.is_connected():
            await self.client.disconnect()

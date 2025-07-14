"""
CSV recorder – appends rows to a timestamped CSV file.
Supports optional custom headers and an optional prefix column.
"""
from __future__ import annotations
import csv, datetime, pathlib

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

class CSVRecorder:
    def __init__(self, prefix: str = "session", headers: list[str] | None = None):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._path   = DATA_DIR / f"{prefix}_{ts}.csv"
        self._file   = self._path.open("w", newline="")
        self._writer = csv.writer(self._file)

        default_headers = ["segment",
                           "timestamp_ms",
                           "acc_x", "acc_y", "acc_z",
                           "gyro_x", "gyro_y", "gyro_z"]
        self._writer.writerow(headers or default_headers)
        self.closed = False

    # ────────────────────────────────────────────────────────────
    @property
    def path(self) -> pathlib.Path:
        return self._path

    # append rows as-is
    def add_rows(self, rows: list[tuple]):
        if not self.closed:
            self._writer.writerows(rows)

    # append rows with a leading value
    def add_rows_with_prefix(self, prefix, rows: list[tuple]):
        if not self.closed:
            self._writer.writerows([(prefix, *r) for r in rows])

    def close(self):
        if not self.closed:
            self._file.close()
            self.closed = True
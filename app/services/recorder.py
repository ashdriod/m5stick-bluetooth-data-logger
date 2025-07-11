"""
CSV recorder – appends rows to a timestamped CSV file.
Accepts optional custom column headers.
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

        default_headers = ["timestamp_ms",
                           "acc_x", "acc_y", "acc_z",
                           "gyro_x", "gyro_y", "gyro_z"]
        self._writer.writerow(headers or default_headers)
        self.closed = False

    # ────────────────────────────────────────────────────────────
    @property
    def path(self) -> pathlib.Path:                    # for GUI display
        return self._path

    def add_rows(self, rows: list[tuple]):            # fast batch append
        if not self.closed:
            self._writer.writerows(rows)

    def close(self) -> None:
        if not self.closed:
            self._file.close()
            self.closed = True
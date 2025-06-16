"""CSV recording utility."""
import csv, datetime, pathlib

DATA_DIR = pathlib.Path("data")
DATA_DIR.mkdir(exist_ok=True)

def open_new_csv(prefix: str = "session") -> tuple[pathlib.Path, csv.writer]:
    ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = DATA_DIR / f"{prefix}_{ts}.csv"
    f = path.open("w", newline="")
    writer = csv.writer(f)
    writer.writerow(["timestamp_ms",
                     "acc_x", "acc_y", "acc_z",
                     "gyro_x", "gyro_y", "gyro_z"])
    return path, writer

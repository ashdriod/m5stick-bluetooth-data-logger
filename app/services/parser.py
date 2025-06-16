"""Parse raw byte payload from M5StickC BLE notifications into numbers."""

import struct, time

PACKET_FORMAT = "<6h"   # 6 * 16-bit little-endian signed ints

def parse(payload: bytes):
    values = struct.unpack(PACKET_FORMAT, payload)
    timestamp = int(time.time() * 1000)
    return (timestamp, *values)

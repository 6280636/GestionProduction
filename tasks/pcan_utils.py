# pcan_utils.py
import threading
import can

_bus = None
bus_lock = threading.Lock()

DEFAULT_IFACE = "PCAN_USBBUS1"
DEFAULT_BITRATE = 50000  # 50 kbit/s

def get_bus():
    global _bus
    if _bus is not None:
        return _bus
    _bus = can.interface.Bus(
        channel=DEFAULT_IFACE,
        interface="pcan",
        bitrate=DEFAULT_BITRATE,
        fd=False
    )
    return _bus

def shutdown_bus():
    global _bus
    if _bus is not None:
        try:
            _bus.shutdown()
        finally:
            _bus = None

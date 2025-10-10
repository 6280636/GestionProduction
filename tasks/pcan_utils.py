import can, threading, atexit

# 🔒 Lock global para evitar acceso simultáneo al bus
bus_lock = threading.Lock()

# 🔄 Variable global que mantiene el bus activo
bus = None

def get_bus():
    """
    Devuelve una instancia global del bus PCAN.
    Si no existe, la crea e inicializa.
    """
    global bus
    if bus is None:
        print("⚙️ Inicializando bus PCAN global...")
        bus = can.interface.Bus(interface="pcan", channel="PCAN_USBBUS1", bitrate=50000)
        print("✅ Bus PCAN inicializado correctamente")
    return bus



def shutdown_bus():
    """
    Cierra el bus PCAN global si está abierto.
    Se llama automáticamente al salir del servidor Django.
    """
    global bus
    if bus is not None:
        try:
            print("🔻 Cerrando bus PCAN...")
            bus.shutdown()
        except Exception as e:
            print(f"⚠️ Error al cerrar bus: {e}")
        finally:
            bus = None
            print("✅ Bus PCAN cerrado correctamente")

# 👉 Registrar el cierre automático al terminar el servidor
atexit.register(shutdown_bus)

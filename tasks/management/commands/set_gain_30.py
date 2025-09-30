from django.core.management.base import BaseCommand
import can
import time

class Command(BaseCommand):
    help = "Ajusta el Gain de la sonda a 30 y muestra todo en la consola"

    def handle(self, *args, **kwargs):
        TARGET_GAIN = 30

        # Inicializar bus PCAN
        bus = can.interface.Bus(interface='pcan', channel='PCAN_USBBUS1', bitrate=50000)

        try:
            # Leer gain actual
            msg_gain_req = can.Message(
                arbitration_id=0x601,
                is_extended_id=False,
                data=[0x4F, 0x30, 0x21, 0x03, 0x00, 0x00, 0x00, 0x00]
            )
            bus.send(msg_gain_req)
            print("📤 Solicitud de Gain enviada")
            
            start = time.time()
            gain_actual = None
            while time.time() - start < 3:
                msg = bus.recv(timeout=0.5)
                if msg and msg.arbitration_id == 0x581 and msg.data[0] == 0x4F:
                    gain_actual = msg.data[4]
                    print(f"📥 Gain actual leído: {gain_actual}")
                    break

            if gain_actual is None:
                print("⚠️ No se pudo leer Gain")
                return

            # Escribir nuevo gain (30)
            msg_gain_write = can.Message(
                arbitration_id=0x601,
                is_extended_id=False,
                data=[0x2F, 0x30, 0x21, 0x03, TARGET_GAIN & 0xFF, 0x00, 0x00, 0x00]
            )
            bus.send(msg_gain_write)
            print(f"📤 Enviando Gain nuevo: {TARGET_GAIN}")
            time.sleep(0.5)  # espera para que el bus procese

            # Leer gain de nuevo para verificar
            bus.send(msg_gain_req)
            start = time.time()
            gain_verif = None
            while time.time() - start < 3:
                msg = bus.recv(timeout=0.5)
                if msg and msg.arbitration_id == 0x581 and msg.data[0] == 0x4F:
                    gain_verif = msg.data[4]
                    print(f"📥 Gain verificado: {gain_verif}")
                    break

            if gain_verif == TARGET_GAIN:
                print("✅ Gain ajustado correctamente a 30")
            else:
                print("❌ Error: Gain no se ajustó correctamente")

        finally:
            bus.shutdown()
            print("✅ Bus PCAN cerrado correctamente")

        # python manage.py set_gain_30


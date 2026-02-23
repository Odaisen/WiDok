from micropython import const
import asyncio
import aioble
import bluetooth
import struct
from machine import Pin

# Bluetooth initialization
def _bluetooth_initialize(Device):
    _BLE_SERVICE_WAND_UUID = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
    _BLE_SERVICE_DOCK_UUID = bluetooth.UUID("9694a3c2-101b-4693-bc53-fe92dae8a9e2")
    _BLE_IMU_CHAR_ID = bluetooth.UUID("444a2375-6b8c-44e3-a058-c375180896d8")
    # Add any variable as _BLE_*device*_CHAR_ID
    if Device=="WAND":
        try:
            _BLE_SERVICE = aioble.Service("_BLE_SERVICE_WAND_UUID")
            IMU_characteristic = aioble.Characteristic(_BLE_SERVICE, _BLE_IMU_CHAR_ID, read=True, write=True, notify=True, capture=True)
            return True
        except Exception as e:
            print("Failed bluetooth initialization:", e)
            return False
    elif Device=="DOCK":
        try:
            # Input all code needed for dock bluetooth initialization
            return True
        except Exception as e:
            print("Failed bluetooth initialization: ", e)
            return False
    else:
        print("Unknown Device.")
        return None


def _bluetooth_encode(data):
    return str(data).encode("utf-8")

def _bluetooth_decode(data):
    try:
        if isinstance(data, bytes):
            return int.from_bytes(data, "big")
        elif isinstance(data, str):
            return int(data)
        return data
    except Exception as e:
        print("Error decoding data:", e)
        return None

async def _bluetooth_write(data, characteristic):
    characteristic.write(_bluetooth_encode(data), send_update=True)
    await asyncio.sleep(0.1)

async def _bluetooth_await_connection_wand():
    while True:
        try:
            async with await aioble.advertise(
                _ADV_INTERNAL_MS,
                name="WiDok-Wand",
                services=[BLE_SERVICE],
                ) as connection:
                    print("Connected to: ", connection.device)
                    await connection.disconnected()
        except asyncio.CancelledError:
            print("Await Connection Cancelled")
        except Exception as e:
            print("Error while awaiting connection: ", e)
        finally:
            await asyncio.sleep(0.1)

async def _bluetooth_wait_write(characteristic):
    while True:
        try:
            connection, data = await characteristic.written()
            print(data)
            print(type)
            data = _bluetooth_decode(data)
            print('Connection: ', connection)
            print('Data: ', data)
            return data
        except asyncio.CancelledError:
            print("Await Write Cancelled")
        except Exception as e:
            print("Error while awaiting write: ", e)
        finally:
            await asyncio.sleep(0.1)


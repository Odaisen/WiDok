# Programmer: Odaisen
# Last Update: 07/05/26

import uasyncio as asyncio
import aioble
import bluetooth
import struct
import sys
import time
import resources.user_signaling as io

try:
    import resources.imu as imu
except Exception as e:
    imu = None
    io.signal(101, e)

try:
    import resources.led_control as addr_leds
except Exception as e:
    addr_leds = None
    print("Adressable led import failed: ", e)
    io.signal(107, e)

aioble.config(mtu=96)
SERVICE_UUID        =   bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID        =   bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID      =   bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID         =   bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID        =   bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")
ADV_INTERVAL_US     =   250_000
DEVICE_NAME         =   "WiDok-Wand"
imu_raw_data        =   (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
imu_fused_data      =   (0, 1.0, 0.0, 0.0, 0.0)
system_data         =   (0, 0.0, 0, 0)
service             =   aioble.Service(SERVICE_UUID)
imu_raw_char        =   aioble.Characteristic(service, IMU_RAW_UUID, notify=True)
imu_fused_char      =   aioble.Characteristic(service, IMU_FUSED_UUID, notify=True)
system_char         =   aioble.Characteristic(service, SYSTEM_UUID, notify=True)
control_char        =   aioble.Characteristic(service, CONTROL_UUID, write=True, capture=True)
aioble.register_services(service)

# Returns True if client has enabled notify bit (fixes bug if client cannot enable notify)
def _cccd_enabled(char):
    try:
        h = getattr(char, "cccd_handle", None) or getattr(char, "_cccd_handle", None)
        ble_obj = getattr(aioble, "_ble", None)
        if h is None or ble_obj is None:
            return False
        val = ble_obj.gatts_read(h)
        if not val:
            return False
        # bit0 = notifications, bit1 = indications
        return bool(val[0] & 0x01)
    except Exception:
        return False

def encode_imu_raw(ts, ax, ay, az, gx, gy, gz):
    return struct.pack("<Iffffff", ts, ax, ay, az, gx, gy, gz)
def encode_imu_fused(ts, qw, qx, qy, qz):
    return struct.pack("<Iffff", ts, qw, qx, qy, qz)
def encode_system(ts, battery_v, battery_pct, flags):
    return struct.pack("<IfBB", ts, battery_v, battery_pct, flags)
'''
Letter definitions:
I - Unsigned int    (4 bytes)
f - Float           (4 bytes)
H - Unsigned short  (2 bytes)
B - Unsigned byte   (1 byte)
b - Signed byte     (1 byte)
'''

async def send_imu_raw(connection):
    while True:
        try:
            data = imu_raw_data
            if isinstance(data, tuple) and len(data) == 7:
                payload = encode_imu_raw(*data)
                imu_raw_char.write(payload)
                await imu_raw_char.notify(connection)

            await asyncio.sleep(0.02)

        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(104, e)

async def send_imu_fused(connection):
    while True:
        try:
            data = imu_fused_data
            if isinstance(data, tuple) and len(data) == 5:
                payload = encode_imu_fused(*data)
                imu_fused_char.write(payload)
                await imu_fused_char.notify(connection)

            await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(104, e)

async def send_system(connection):
    while True:
        try:
            data = system_data
            if isinstance(data, tuple) and len(data) == 4:
                payload = encode_system(*data)
                system_char.write(payload)
                await system_char.notify(connection)

            await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(105, e)

# Checks writable bits and handles commands
async def handle_control():
    while True:
        try:
            conn, data = await control_char.written()
            if not data:
                continue
            cmd = data[0]
            if cmd == 1:
                print("LED command received")
                addr_leds.set_mode("rainbow")

            elif cmd == 2:
                print("Reset requested")
                try:
                    if imu:
                        imu.reset()
                except Exception as e:
                    io.signal(104, e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(103, e)

# Advertises device, publishes data after connect, stops publishing after disconnect
async def ble_main():
    while True:
        try:
            print("Advertising...")
            connection = await aioble.advertise(
                ADV_INTERVAL_US,
                name=DEVICE_NAME,
                services=[SERVICE_UUID],
            )
            print("Connected:", connection.device)
            await asyncio.sleep_ms(500)
            t1 = asyncio.create_task(send_imu_raw(connection))
            t2 = asyncio.create_task(send_imu_fused(connection))
            t3 = asyncio.create_task(send_system(connection))
            t4 = asyncio.create_task(handle_control())
            await connection.disconnected()
            for t in (t1, t2, t3, t4):
                t.cancel()
            for t in (t1, t2, t3, t4):
                try:
                    await t
                except asyncio.CancelledError:
                    pass
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(103, e)
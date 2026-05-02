# Programmer: Odaisen
# Last Update: 01/05/26

# =========================
# IMPORTS
# =========================

import uasyncio as asyncio
import aioble
import bluetooth
import struct
import time

# =========================
# UUIDs
# =========================

SERVICE_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID    = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")

ADV_INTERVAL_US = 250_000

# =========================
# BLE STATE (filled by main)
# =========================

imu_raw_data = (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
imu_fused_data = (0, 1.0, 0.0, 0.0, 0.0)
system_data = (0, 0.0, 0, 0)

# =========================
# SERVICE SETUP
# =========================

aioble.config(mtu=96)

service =           aioble.Service(SERVICE_UUID)

imu_raw_char =      aioble.Characteristic(service, IMU_RAW_UUID, notify=True)
imu_fused_char =    aioble.Characteristic(service, IMU_FUSED_UUID, notify=True)
system_char =       aioble.Characteristic(service, SYSTEM_UUID, notify=True)

control_char =      aioble.Characteristic(service, CONTROL_UUID, write=True, capture=True)

aioble.register_services(service)

# =========================
# ENCODERS
# =========================

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

'''
All data that should be public (may not be implemented)
Device Name
Firmware Version
Timestamp
Battery percentage
Position vs starting position
Rotation
Interrupt 1 status IMU
Interrupt 2 status IMU
CPU Temp or other data
LED status / colour
'''

# =========================
# TASKS
# =========================

async def send_imu_raw(connection):
    global imu_raw_data
    while True:
        try:
            data = imu_raw_data
            if isinstance(data, tuple) and len(data) == 7:
                await imu_raw_char.notify(connection, encode_imu_raw(*data))
            await asyncio.sleep(0.02)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("IMU Raw send error:", e)
        await asyncio.sleep(0.1)

async def send_imu_fused(connection):
    global imu_fused_data
    while True:
        try:
            data = imu_fused_data
            if isinstance(data, tuple) and len(data) == 5:
                await imu_fused_char.notify(connection, encode_imu_fused(*data))
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("IMU Fused send error:", e)
        await asyncio.sleep(0.2)

async def send_system(connection):
    global system_data
    while True:
        try:
            data = system_data
            if isinstance(data, tuple) and len(data) == 4:
                await system_char.notify(connection, encode_system(*data))
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("System send error:", e)
        await asyncio.sleep(0.5)


async def handle_control():
    while True:
        try:
            conn, data = await control_char.written()
            cmd = data[0]

            if cmd == 1:
                print("LED command received")

            elif cmd == 2:
                print("Reset requested")

        except asyncio.CancelledError:
            break


# =========================
# MAIN BLE LOOP
# =========================

async def ble_main():
    while True:
        try:
            print("Advertising...")
            connection = await aioble.advertise(
                ADV_INTERVAL_US,
                name="WiDok-Wand",
                services=[SERVICE_UUID],
            )
            print("Connected:", connection.device)
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
            print("Exception in ble_main:", e)
            await asyncio.sleep(0.5)
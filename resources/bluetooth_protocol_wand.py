# Programmer: Odaisen
# Last Update: 30/04/26

import asyncio
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

imu_raw_data = None
imu_fused_data = None
system_data = None

# =========================
# SERVICE SETUP
# =========================

service = aioble.Service(SERVICE_UUID)

imu_raw_char = aioble.Characteristic(service, IMU_RAW_UUID, notify=True)
imu_fused_char = aioble.Characteristic(service, IMU_FUSED_UUID, notify=True)
system_char = aioble.Characteristic(service, SYSTEM_UUID, notify=True)

control_char = aioble.Characteristic(service, CONTROL_UUID, write=True, capture=True)

aioble.register_services(service)

# =========================
# ENCODERS
# =========================

def encode_imu_raw(ts, ax, ay, az, gx, gy, gz):
    return struct.pack("<Iffffff", ts, ax, ay, az, gx, gy, gz)

def encode_imu_fused(ts, qw, qx, qy, qz):
    return struct.pack("<Iffff", ts, qw, qx, qy, qz)

def encode_system(ts, battery_mv, battery_pct, flags):
    return struct.pack("<IHBb", ts, battery_mv, battery_pct, flags)

# =========================
# TASKS
# =========================

async def send_imu_raw(connection):
    global imu_raw_data
    while True:
        if imu_raw_data:
            imu_raw_char.notify(connection, encode_imu_raw(*imu_raw_data))
        await asyncio.sleep(0.02)


async def send_imu_fused(connection):
    global imu_fused_data
    while True:
        if imu_fused_data:
            imu_fused_char.notify(connection, encode_imu_fused(*imu_fused_data))
        await asyncio.sleep(0.1)


async def send_system(connection):
    global system_data
    while True:
        if system_data:
            system_char.notify(connection, encode_system(*system_data))
        await asyncio.sleep(1)


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
        async with await aioble.advertise(
            ADV_INTERVAL_US,
            name="WiDok-Wand",
            services=[SERVICE_UUID],
        ) as connection:

            print("Connected:", connection.device)

            t1 = asyncio.create_task(send_imu_raw(connection))
            t2 = asyncio.create_task(send_imu_fused(connection))
            t3 = asyncio.create_task(send_system(connection))
            t4 = asyncio.create_task(handle_control())

            await connection.disconnected()

            t1.cancel()
            t2.cancel()
            t3.cancel()
            t4.cancel()

            await asyncio.sleep(0.1)
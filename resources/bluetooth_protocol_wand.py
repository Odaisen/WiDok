# Programmer: Odaisen
# BLE Protocol Implementation (WAND)

import asyncio
import aioble
import bluetooth
import struct
import time
import gc

# =========================
# UUID DEFINITIONS
# =========================

SERVICE_UUID      = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID      = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID    = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID       = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID      = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")
CONFIG_UUID       = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb8")

ADV_INTERVAL_US = 250_000  # 250 ms

# =========================
# SERVICE SETUP
# =========================

service = aioble.Service(SERVICE_UUID)

imu_raw_char = aioble.Characteristic(service, IMU_RAW_UUID, notify=True)
imu_fused_char = aioble.Characteristic(service, IMU_FUSED_UUID, notify=True)

system_char = aioble.Characteristic(service, SYSTEM_UUID, read=True, notify=True)

control_char = aioble.Characteristic(service, CONTROL_UUID, write=True, capture=True)
config_char = aioble.Characteristic(service, CONFIG_UUID, read=True, write=True)

aioble.register_services(service)

# =========================
# ENCODING FUNCTIONS
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

async def send_imu(connection):
    while True:
        try:
            ts = time.ticks_ms()

            # TODO: Replace with real IMU data
            ax, ay, az = 0.0, 0.0, 1.0
            gx, gy, gz = 0.0, 0.0, 0.0

            data = encode_imu_raw(ts, ax, ay, az, gx, gy, gz)
            imu_raw_char.notify(connection, data)

            await asyncio.sleep(0.02)  # ~50 Hz

        except asyncio.CancelledError:
            break


async def send_fused(connection):
    while True:
        try:
            ts = time.ticks_ms()

            # TODO: Replace with real fused data
            qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0

            data = encode_imu_fused(ts, qw, qx, qy, qz)
            imu_fused_char.notify(connection, data)

            await asyncio.sleep(0.1)  # 10 Hz

        except asyncio.CancelledError:
            break


async def send_system(connection):
    while True:
        try:
            ts = time.ticks_ms()

            # TODO: Replace with real battery reading
            battery_mv = 3700
            battery_pct = 85

            flags = 0
            flags |= 1 << 3  # BLE connected

            data = encode_system(ts, battery_mv, battery_pct, flags)
            system_char.notify(connection, data)

            await asyncio.sleep(1)

        except asyncio.CancelledError:
            break


async def handle_control():
    while True:
        try:
            connection, data = await control_char.written()

            cmd = data[0]

            if cmd == 1:  # Set LED
                r, g, b = struct.unpack("<BBB", data[1:4])
                print("Set LED:", r, g, b)

            elif cmd == 2:  # Reset position
                print("Reset position")

            elif cmd == 3:  # Set mode
                mode = data[1]
                print("Mode:", mode)

            elif cmd == 4:
                print("Calibration requested")

        except asyncio.CancelledError:
            break


# =========================
# MAIN LOOP
# =========================

async def main():
    while True:
        print("Advertising...")

        async with await aioble.advertise(
            ADV_INTERVAL_US,
            name="WiDok-Wand",
            services=[SERVICE_UUID],
        ) as connection:

            print("Connected:", connection.device)

            imu_task = asyncio.create_task(send_imu(connection))
            fused_task = asyncio.create_task(send_fused(connection))
            sys_task = asyncio.create_task(send_system(connection))
            ctrl_task = asyncio.create_task(handle_control())

            await connection.disconnected()

            print("Disconnected")

            imu_task.cancel()
            fused_task.cancel()
            sys_task.cancel()
            ctrl_task.cancel()

            await asyncio.sleep(0.1)


# =========================
# RUN
# =========================

asyncio.run(main())
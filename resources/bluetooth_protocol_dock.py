# Programmer: Grok / Justin
# Last Update: 07/05/26

import uasyncio as asyncio
import aioble
import bluetooth
import struct
from machine import Pin

# ================== EXACT MATCH FROM YOUR HOST ==================
DEVICE_NAME      = "WiDok-Wand"
SERVICE_UUID     = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID     = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID      = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID     = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")

# Global handles so other parts of your code can read the latest data
latest_imu_raw   = None
latest_imu_fused = None
latest_system    = None
connection       = None
control_char     = None

async def connect_to_wand():
    global connection, control_char
    print("Scanning for WiDok-Wand...")

    async for adv in aioble.scan(5000, active=True):
        if adv.name() == DEVICE_NAME or SERVICE_UUID in adv.services():
            print("Found WiDok-Wand:", adv.device)
            try:
                connection = await aioble.connect(adv.device)
                print("Connected to WiDok-Wand!")

                service = await connection.service(SERVICE_UUID)

                # Get all characteristics
                raw_char   = await service.characteristic(IMU_RAW_UUID)
                fused_char = await service.characteristic(IMU_FUSED_UUID)
                sys_char   = await service.characteristic(SYSTEM_UUID)
                control_char = await service.characteristic(CONTROL_UUID)

                # Subscribe to notifications (the host pushes data)
                await raw_char.subscribe(notify=True)
                await fused_char.subscribe(notify=True)
                await sys_char.subscribe(notify=True)

                print("Subscribed to all notifications")

                # Start background receivers
                asyncio.create_task(receive_imu_raw(raw_char))
                asyncio.create_task(receive_imu_fused(fused_char))
                asyncio.create_task(receive_system(sys_char))

                return True
            except Exception as e:
                print("Connection failed:", e)
                await asyncio.sleep_ms(1000)
    print("WiDok-Wand not found")
    return False

async def receive_imu_raw(char):
    global latest_imu_raw
    while True:
        try:
            data = await char.notified()
            latest_imu_raw = struct.unpack("<Iffffff", data)  # ts, ax, ay, az, gx, gy, gz
            print(f"IMU RAW → {latest_imu_raw}")
            # You can later push this to TFT or use it for anything
        except Exception:
            await asyncio.sleep_ms(100)

async def receive_imu_fused(char):
    global latest_imu_fused
    while True:
        try:
            data = await char.notified()
            latest_imu_fused = struct.unpack("<Iffff", data)  # ts, qw, qx, qy, qz
            print(f"IMU FUSED → {latest_imu_fused}")
        except Exception:
            await asyncio.sleep_ms(100)

async def receive_system(char):
    global latest_system
    while True:
        try:
            data = await char.notified()
            latest_system = struct.unpack("<IfBB", data)  # ts, battery_v, battery_pct, flags
            print(f"SYSTEM → Battery {latest_system[1]:.2f}V  {latest_system[2]}%")
        except Exception:
            await asyncio.sleep_ms(100)

async def send_command(cmd: int):
    """Example: send command to host (1 = rainbow LEDs, 2 = reset IMU)"""
    global control_char
    if control_char and connection:
        try:
            await control_char.write(struct.pack("B", cmd), response=True)
            print(f"Sent command {cmd} to host")
        except Exception as e:
            print("Command failed:", e)

# ====================== START EVERYTHING ======================
async def ble_client_main():
    while True:
        if not connection or not connection.is_connected:
            await connect_to_wand()
        await asyncio.sleep_ms(2000)   # retry every 2 seconds if disconnected
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

# ================== PROPER INITIALIZATION ==================
aioble.config(mtu=96)                    # Same as your host
ble = bluetooth.BLE()
ble.active(True)                         # Explicitly turn on BLE radio

async def connect_to_wand():
    global connection, control_char
    print("Scanning for WiDok-Wand...")

    # Correct context-manager style (this fixes the AssertionError)
    async with aioble.scan(5000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for adv in scanner:
            if adv.name() == DEVICE_NAME or SERVICE_UUID in adv.services():
                print("Found WiDok-Wand:", adv.device)
                try:
                    # THIS IS THE FIXED LINE:
                    connection = await adv.device.connect(timeout_ms=8000)
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
    print("IMU RAW receiver started")
    global latest_imu_raw
    while True:
        try:
            data = await char.notified()
            print("raw bytes received:",data)
            latest_imu_raw = struct.unpack("<Iffffff", data)  # ts, ax, ay, az, gx, gy, gz
            print(f"IMU RAW → {latest_imu_raw}")
            # You can later push this to TFT or use it for anything
        except Exception as e:
            print("IMU RAW failed:", e)
            await asyncio.sleep_ms(200)

async def receive_imu_fused(char):
    print("IMU FUSED receiver started")
    global latest_imu_fused
    while True:
        try:
            data = await char.notified()
            print("imu fused bytes received:",data)
            latest_imu_fused = struct.unpack("<Iffff", data)  # ts, qw, qx, qy, qz
            print(f"IMU FUSED → {latest_imu_fused}")
        except Exception as e:
            print("IMU FUSED failed:", e)
            await asyncio.sleep_ms(200)

async def receive_system(char):
    print("SYSTEM receiver started")
    global latest_system
    while True:
        try:
            data = await char.notified()
            print("system bytes received:",data)
            latest_system = struct.unpack("<IfBB", data)  # ts, battery_v, battery_pct, flags
            print(f"SYSTEM → Battery {latest_system[1]:.2f}V  {latest_system[2]}%")
        except Exception as e:
            print("SYSTEM failed:", e)
            await asyncio.sleep_ms(200)

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
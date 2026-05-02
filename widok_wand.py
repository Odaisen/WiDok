# Programmer: Odaisen
# Last Update: 01/05/26

# =========================
# IMPORTS
# =========================

import uasyncio as asyncio
import time

from machine import Pin, I2C

try:
    import resources.imu as imu
except Exception as e:
    print("IMU Initialization Failed: ", e)

try:
    import resources.bluetooth_protocol_wand as ble
except Exception as e:
    print("Bluetooth Initialization Failed: ", e)

try:
    import resources.battery_sensing as bat
except Exception as e:
    print("Battery Sensing Initialization Failed: ", e)

''' 
IO8     - LED DI
IO18    - LED BI
IO21    - I2C SCL
IO14    - I2C SDA
IO13    - INT1 IMU
IO12    - INT2 IMU
IO35    - Battery sensing (DO NOT USE IO35)
IO6     - Indicator LED
IO3     - Out Extra 1
IO46    - Out Extra 2 (Cannot be used)
IO9     - Out Extra 3
IO10    - Out Extra 4 (BATTERY SENSING)
'''

# =========================
# IMU LOOP
# =========================

async def imu_loop():
    while True:
        try:
            imu.update()

            ax, ay, az, gx, gy, gz = imu.read_raw()
            qw, qx, qy, qz = imu.get_fused()

            ts = time.ticks_ms()

            ble.imu_raw_data = (ts, ax, ay, az, gx, gy, gz)
            ble.imu_fused_data = (ts, qw, qx, qy, qz)

            await asyncio.sleep(0.01)
        except Exception as e:
            print("Exception in IMU-Loop: ", e)


# =========================
# SYSTEM LOOP
# =========================

async def system_loop():
    while True:
        try:
            ts = time.ticks_ms()
            try:
                res = bat.read_battery_v()
                if isinstance(res, tuple) and len(res) >= 2:
                    battery_v, battery_pct = res[:2]
                else:
                    battery_v, battery_pct = 0.0, 0
            except Exception as e:
                print("Battery read failed: ", e)
            flags = 0

            ble.system_data = (ts, battery_v, battery_pct, flags)

            await asyncio.sleep(5)
        except asyncio.CancelledError:
            break


# =========================
# DIAGNOSTIC LOOP
# =========================

async def diagnostic_loop(i2c):
    print("Diagnosing...")
    while True:
        try:
            ts = time.ticks_ms()

            print("Time: ", ts)
            #print("I2C Scan:", i2c.scan())

            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break


# =========================
# MAIN
# =========================

async def main():
    i2c = imu.init()
    imu_task = asyncio.create_task(imu_loop())
    sys_task = asyncio.create_task(system_loop())
    ble_task = asyncio.create_task(ble.ble_main())
    diag_task = asyncio.create_task(diagnostic_loop(i2c))
    await asyncio.gather(imu_task, sys_task, ble_task, diag_task)
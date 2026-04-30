# Programmer: Odaisen
# Last Update: 30/04/26

import asyncio
import time

import resources.imu as imu
import resources.bluetooth_protocol_wand as ble


# =========================
# IMU LOOP
# =========================

async def imu_loop():
    while True:
        imu.update()

        ax, ay, az, gx, gy, gz = imu.read_raw()
        qw, qx, qy, qz = imu.get_fused()

        ts = time.ticks_ms()

        ble.imu_raw_data = (ts, ax, ay, az, gx, gy, gz)
        ble.imu_fused_data = (ts, qw, qx, qy, qz)

        await asyncio.sleep(0.01)


# =========================
# SYSTEM LOOP
# =========================

async def system_loop():
    while True:
        ts = time.ticks_ms()

        battery_mv = 3700
        battery_pct = 85
        flags = 0

        ble.system_data = (ts, battery_mv, battery_pct, flags)

        await asyncio.sleep(1)


# =========================
# MAIN
# =========================

async def main():
    imu_task = asyncio.create_task(imu_loop())
    sys_task = asyncio.create_task(system_loop())
    ble_task = asyncio.create_task(ble.ble_main())

    await asyncio.gather(imu_task, sys_task, ble_task)


asyncio.run(main())
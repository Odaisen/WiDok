# Programmer: Odaisen
# Last Update: 30/04/26

# =========================
# IMPORTS
# =========================

import asyncio
import resources.bluetooth_protocol_wand as ble
import resources.imu as imu

# =========================
# PIN DEFINITIONS
# =========================
'''
IO8 - LED DI
IO18 - LED BI

IO21 - I2C CLK
IO14 - I2C D
IO13 - INT1 IMU
IO12 - INT2 IMU

IO35 - Battery sensing
IO6 - Indicator LED

IO3 - Out Extra 1
IO46 - Out Extra 2
IO9 - Out Extra 3
IO10 - Out Extra 4
'''

# =========================
# BLUETOOTH INITIALIZATION
# =========================


# =========================
# MAIN LOOP
# =========================

async def main():
    write_IMU = asyncio.create_task(_bluetooth_write(characteristic="_BLE_IMU_CHAR_ID"))
    await_connection = asyncio.create_task(_bluetooth_await_connection())
    await asyncio.gather(write_IMU, await_connection)

asyncio.run(main())

'''
All public bluetooth data:
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
# Programmer: Odaisen
# Last Update: 02/05/26 (improved)

import uasyncio as asyncio
import time
try:
    import resources.user_signaling as io
except Exception as e:
    io = None
    try:
        print("IO Initialization Failed:", e)
    except Exception:
        pass
try:
    import resources.imu as imu
except Exception as e:
    try:
        print("IMU import failed:", e)
    except Exception:
        pass
    imu = None
    if io:
        io.signal(102, "wand", e)
try:
    import resources.bluetooth_protocol_wand as ble
except Exception as e:
    try:
        print("BLE import failed:", e)
    except Exception:
        pass
    ble = None
    if io:
        io.signal(102, "wand", e)
try:
    import resources.battery_sensing as bat
except Exception as e:
    try:
        print("Battery sensing import failed:", e)
    except Exception:
        pass
    bat = None
    if io:
        io.signal(102, "wand", e)
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
async def imu_loop():
    if imu is None or ble is None:
        return
    while True:
        try:
            imu.update()
            ax, ay, az, gx, gy, gz = imu.read_raw()
            qw, qx, qy, qz = imu.get_fused()
            ts = time.ticks_ms() & 0xFFFFFFFF  # ensure 32-bit
            ble.imu_raw_data = (ts, ax, ay, az, gx, gy, gz)
            ble.imu_fused_data = (ts, qw, qx, qy, qz)
            await asyncio.sleep_ms(10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            if io:
                io.signal(104, "wand", e)
            await asyncio.sleep_ms(100)
async def system_loop():
    if ble is None:
        return
    while True:
        try:
            ts = time.ticks_ms() & 0xFFFFFFFF
            battery_v, battery_pct = 0.0, 0
            if bat:
                try:
                    res = bat.read_battery_v()
                    if isinstance(res, tuple) and len(res) >= 2:
                        battery_v, battery_pct = res[:2]
                except Exception as e:
                    print("Battery read failed:", e)
                    if io:
                        io.signal(105, "wand", e)
            flags = 0
            ble.system_data = (ts, battery_v, battery_pct, flags)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            if io:
                io.signal(101, "wand", e)
            await asyncio.sleep(0.5)
async def diagnostic_loop(i2c, enabled=True):
    if not enabled:
        return
    print("Diagnosing...")
    while True:
        try:
            ts = time.ticks_ms()
            batt_str = "N/A"
            try:
                if bat:
                    batt = bat.read_battery_v()
                    batt_str = "{:.2f} V, {}%".format(batt[0], batt[1])
            except Exception as e:
                batt_str = "read error: {}".format(e)
            print("Time:", ts)
            print("Battery:", batt_str)
            # if i2c: print("I2C Scan:", i2c.scan())
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception as e:
            if io:
                io.signal(101, "wand", e)
            await asyncio.sleep(0.5)
async def main(run_diag=True):
    # Initialize IMU I2C
    i2c = None
    if imu:
        i2c = imu.init()
    tasks = []
    try:
        if imu and ble:
            tasks.append(asyncio.create_task(imu_loop()))
        if ble:
            tasks.append(asyncio.create_task(ble.ble_main()))
        tasks.append(asyncio.create_task(system_loop()))
        tasks.append(asyncio.create_task(diagnostic_loop(i2c, enabled=run_diag)))
        # Await all tasks (they run forever unless cancelled)
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        for t in tasks:
            t.cancel()
        for t in tasks:
            try:
                await t
            except asyncio.CancelledError:
                pass

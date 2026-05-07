# Programmer: Odaisen
# Last Update: 02/05/26

import uasyncio as asyncio
import time

io = None; t = 0
while not io and t < 10:
    try:
        import resources.user_signaling as io
        io.init("wand")
    except Exception as e:
        print("IO import failed:", e)
        time.sleep(1)
        t += 1

try:
    import resources.imu as imu
except Exception as e:
    imu = None
    try: io.signal(102, e)
    except Exception: print("IMU import failed:", e)

try:
    import resources.bluetooth_protocol_wand as ble
except Exception as e:
    ble = None
    try: io.signal(102, e)
    except Exception: print("BLE import failed:", e)

try:
    import resources.battery_sensing as bat
except Exception as e:
    bat = None
    try: io.signal(102, e)
    except Exception: print("Battery import failed:", e)

try:
    import resources.led_control as addr_leds
except Exception as e:
    addr_leds = None
    try: io.signal(107, e)
    except Exception: print("Adressable LED import failed:", e)

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

# Gets IMU data, and publishes it on ble
async def imu_loop():
    if imu is None or ble is None:
        return
    while True:
        try:
            imu.update()
            ax, ay, az, gx, gy, gz = imu.read_raw()
            qw, qx, qy, qz = imu.get_fused()
            ts = time.ticks_ms() & 0xFFFFFFFF
            ble.imu_raw_data = (ts, ax, ay, az, gx, gy, gz)
            ble.imu_fused_data = (ts, qw, qx, qy, qz)
            await asyncio.sleep_ms(10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            try: io.signal(104, e)
            except Exception: print("IMU loop error:", e)
            await asyncio.sleep_ms(100)

# Gets battery data, and publishes it on ble
async def system_loop():
    if bat is None or ble is None:
        return
    while True:
        try:
            ts = time.ticks_ms() & 0xFFFFFFFF
            battery_v, battery_pct = 0.0, 0
            try:
                battery_v, battery_pct = bat.read_battery_v()
            except Exception as e:
                try: io.signal(105, e)
                except Exception: print("Battery read error:", e)
            flags = 0
            ble.system_data = (ts, battery_v, battery_pct, flags)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            try: io.signal(101, e)
            except Exception: print("System loop error:", e)
            await asyncio.sleep(5)

# Diagnostic loop
async def diagnostic_loop(i2c, enabled=True):
    if not enabled:
        return
    print("Diagnosing on")
    while True:
        try:
            ts = time.ticks_ms()
            batt_str = "N/A"
            try:
                if bat:
                    batt = bat.read_battery_v()
                    batt_str = "{:.2f} V, {}%".format(batt[0], batt[1])
            except Exception as e:
                try: io.signal(105, e)
                except Exception: print("Battery diag error:", e)
            print("Time:", ts)
            print("Battery:", batt_str)
            if i2c:
                try:
                    print("I2C Scan:", i2c.scan())
                except Exception as e:
                    try: io.signal(104, e)
                    except Exception: print("I2C scan error:", e)
            await asyncio.sleep(3)
        except asyncio.CancelledError:
            break
        except Exception as e:
            try: io.signal(101, e)
            except Exception: print("Diagnostic loop error:", e)
            await asyncio.sleep(0.5)

async def main(run_diag=False):
    i2c = None
    #if imu:
        #i2c = imu.init()
    led_ok = False
    if addr_leds:
        s = addr_leds.init(device="wand", segments=1, leds_per_segment=20, brightness=0.5)
        if s:
            addr_leds.set_mode("chase", colour=(0,64,128), period_ms=1800)
            led_ok = True
    tasks = []
    try:
        if imu and ble:
            tasks.append(asyncio.create_task(imu_loop()))
        if ble:
            tasks.append(asyncio.create_task(ble.ble_main()))
        if led_ok:
            tasks.append(asyncio.create_task(addr_leds.run()))
        if bat and ble:
            tasks.append(asyncio.create_task(system_loop()))
        if run_diag and i2c:
            tasks.append(asyncio.create_task(diagnostic_loop(i2c, enabled=run_diag)))
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
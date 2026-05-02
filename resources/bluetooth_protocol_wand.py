# Programmer: Odaisen
# Last Update: 02/05/26

import uasyncio as asyncio
import aioble
import bluetooth
import struct
import sys
import time

try:
    import resources.imu as imu
except Exception as e:
    imu = None
    try:
        print("IMU import failed:", e)
    except Exception:
        pass
SERVICE_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID    = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID   = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")
ADV_INTERVAL_US = 250_000
DEVICE_NAME = "WiDok-Wand"
imu_raw_data = (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
imu_fused_data = (0, 1.0, 0.0, 0.0, 0.0)
system_data = (0, 0.0, 0, 0)
aioble.config(mtu=96)
service =           aioble.Service(SERVICE_UUID)
imu_raw_char =      aioble.Characteristic(service, IMU_RAW_UUID, notify=True)
imu_fused_char =    aioble.Characteristic(service, IMU_FUSED_UUID, notify=True)
system_char =       aioble.Characteristic(service, SYSTEM_UUID, notify=True)
control_char =      aioble.Characteristic(service, CONTROL_UUID, write=True, capture=True)

aioble.register_services(service)

def _cccd_enabled(char):
    # Returns True if Notify bit is set for this characteristic’s CCCD
    try:
        h = getattr(char, "cccd_handle", None) or getattr(char, "_cccd_handle", None)
        ble_obj = getattr(aioble, "_ble", None)
        if h is None or ble_obj is None:
            return False
        val = ble_obj.gatts_read(h)
        if not val:
            return False
        # bit0 = notifications, bit1 = indications
        return bool(val[0] & 0x01)
    except Exception:
        return False


def _print_cccd_state():
    try:
        def hpair(ch):
            vh = getattr(ch, "value_handle", None) or getattr(ch, "_value_handle", None)
            chh = getattr(ch, "cccd_handle", None) or getattr(ch, "_cccd_handle", None)
            return vh, chh

        print(
            "Handles imu_raw:", hpair(imu_raw_char),
            "imu_fused:", hpair(imu_fused_char),
            "system:", hpair(system_char)
        )

        vals = []
        for name, ch in (
            ("imu_raw", imu_raw_char),
            ("imu_fused", imu_fused_char),
            ("system", system_char),
        ):
            on = _cccd_enabled(ch)
            vals.append("{}:{}".format(name, "ON" if on else "off"))

        print("CCCD:", ", ".join(vals))
    except Exception as e:
        print("CCCD diag failed:", e)


async def _wait_for_any_subscription(timeout_ms=5000):
    t0 = time.ticks_ms()
    printed = False
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        if not printed:
            print("Waiting for client to enable notifications (toggle Notify in nRF Connect)…")
            _print_cccd_state()
            printed = True

        if (
            _cccd_enabled(imu_raw_char)
            or _cccd_enabled(imu_fused_char)
            or _cccd_enabled(system_char)
        ):
            print("At least one CCCD enabled.")
            return True

        await asyncio.sleep(0.2)

    _print_cccd_state()
    print("No CCCD enabled within timeout; will still run but skip notify until enabled.")
    return False

def encode_imu_raw(ts, ax, ay, az, gx, gy, gz):
    return struct.pack("<Iffffff", ts, ax, ay, az, gx, gy, gz)
def encode_imu_fused(ts, qw, qx, qy, qz):
    return struct.pack("<Iffff", ts, qw, qx, qy, qz)
def encode_system(ts, battery_v, battery_pct, flags):
    return struct.pack("<IfBB", ts, battery_v, battery_pct, flags)
# Letter definitions:
# I - Unsigned int    (4 bytes)
# f - Float           (4 bytes)
# H - Unsigned short  (2 bytes)
# B - Unsigned byte   (1 byte)
# b - Signed byte     (1 byte)
async def send_imu_raw(connection):
    first_ok = True
    while True:
        try:
            if not _cccd_enabled(imu_raw_char):
                await asyncio.sleep(0.1)
                continue

            data = imu_raw_data
            if isinstance(data, tuple) and len(data) == 7:
                payload = encode_imu_raw(*data)
                imu_raw_char.write(payload)
                try:
                    await imu_raw_char.notify(connection)
                except TypeError:
                    # Some aioble builds want no connection argument
                    await imu_raw_char.notify()

                if first_ok:
                    print("imu_raw: first notify OK")
                    first_ok = False

            await asyncio.sleep(0.02)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print("IMU Raw send error:", e)
            try:
                sys.print_exception(e)
            except Exception:
                pass
            await asyncio.sleep(0.2)


async def send_imu_fused(connection):
    first_ok = True
    while True:
        try:
            if not _cccd_enabled(imu_fused_char):
                await asyncio.sleep(0.1)
                continue

            data = imu_fused_data
            if isinstance(data, tuple) and len(data) == 5:
                payload = encode_imu_fused(*data)
                imu_fused_char.write(payload)
                try:
                    await imu_fused_char.notify(connection)
                except TypeError:
                    await imu_fused_char.notify()

                if first_ok:
                    print("imu_fused: first notify OK")
                    first_ok = False

            await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print("IMU Fused send error:", e)
            try:
                sys.print_exception(e)
            except Exception:
                pass
            await asyncio.sleep(0.5)


async def send_system(connection):
    first_ok = True
    while True:
        try:
            if not _cccd_enabled(system_char):
                await asyncio.sleep(0.2)
                continue

            data = system_data
            if isinstance(data, tuple) and len(data) == 4:
                payload = encode_system(*data)
                system_char.write(payload)
                try:
                    await system_char.notify(connection)
                except TypeError:
                    await system_char.notify()

                if first_ok:
                    print("system: first notify OK")
                    first_ok = False

            await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            break
        except Exception as e:
            print("System send error:", e)
            try:
                sys.print_exception(e)
            except Exception:
                pass
            await asyncio.sleep(1.0)

async def handle_control():
    while True:
        try:
            conn, data = await control_char.written()
            if not data:
                continue
            cmd = data[0]
            if cmd == 1:
                print("LED command received")
                # TODO: Add LED handling if desired.
            elif cmd == 2:
                print("Reset requested")
                try:
                    if imu:
                        imu.reset()
                except Exception as e:
                    print("IMU reset failed:", e)
        except asyncio.CancelledError:
            break
        except Exception as e:
            try:
                print("Control handler error:", e)
            except Exception:
                pass
            await asyncio.sleep(0.2)

async def ble_main():
    while True:
        try:
            print("Advertising...")
            connection = await aioble.advertise(
                ADV_INTERVAL_US,
                name=DEVICE_NAME,
                services=[SERVICE_UUID],
            )
            print("Connected:", connection.device)
            await asyncio.sleep_ms(500)
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
            try:
                print("Exception in ble_main:", e)
            except Exception:
                pass
            await asyncio.sleep(0.5)
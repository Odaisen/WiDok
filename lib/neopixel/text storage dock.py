# Programmer: Chat
# Last Update: 07/05/26

import uasyncio as asyncio
import aioble
import bluetooth
import struct
import time
import resources.user_signaling as io
# Optional: if your dock has UI/LEDs/etc, import here.
# try:
#     import resources.dock_ui as dock_ui
# except Exception as e:
#     dock_ui = None
#     io.signal(201, e)
# BLE configuration
aioble.config(mtu=96)
# UUIDs must match the wand
SERVICE_UUID        = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb3")
IMU_RAW_UUID        = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb4")
IMU_FUSED_UUID      = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb5")
SYSTEM_UUID         = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb6")
CONTROL_UUID        = bluetooth.UUID("671201d2-9252-4eab-adbc-ee068e20cbb7")
DEVICE_NAME         = "WiDok-Wand"
SCAN_WINDOW_US      = 30_000
SCAN_INTERVAL_US    = 30_000
SCAN_TIMEOUT_MS     = 7_000
RECONNECT_DELAY_S   = 1.0
# Latest data caches (updated upon notifications); tuples mirror wand encodings
imu_raw_latest      = None  # (ts, ax, ay, az, gx, gy, gz)
imu_fused_latest    = None  # (ts, qw, qx, qy, qz)
system_latest       = None  # (ts, battery_v, battery_pct, flags)
# Async queues for consumers (if you want to stream data to other tasks)
imu_raw_queue       = asyncio.Queue(10)
imu_fused_queue     = asyncio.Queue(10)
system_queue        = asyncio.Queue(10)
# -----------------------------------------------------------------------------
# Decoders (must match wand's encodings)
# -----------------------------------------------------------------------------
def decode_imu_raw(buf):
    # <Iffffff  -> (uint32, 6 floats)
    if len(buf) != struct.calcsize("<Iffffff"):
        raise ValueError("IMU raw packet size mismatch")
    return struct.unpack("<Iffffff", buf)
def decode_imu_fused(buf):
    # <Iffff  -> (uint32, 4 floats)
    if len(buf) != struct.calcsize("<Iffff"):
        raise ValueError("IMU fused packet size mismatch")
    return struct.unpack("<Iffff", buf)
def decode_system(buf):
    # <IfBB  -> (uint32, float, uint8, uint8)
    if len(buf) != struct.calcsize("<IfBB"):
        raise ValueError("System packet size mismatch")
    return struct.unpack("<IfBB", buf)
# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
async def _queue_put_latest(q, item):
    # Keep the queue from growing unbounded; drop oldest if full
    if q.full():
        try:
            _ = q.get_nowait()
        except Exception:
            pass
    await q.put(item)
def _adv_matches(adv):
    # Prefer matching by advertised service UUID for robustness; fallback to name
    try:
        services = adv.services()
        if services:
            # Compare 128-bit UUIDs, if present (aioble normalizes to bluetooth.UUID)
            for s in services:
                if s == SERVICE_UUID:
                    return True
        name = adv.name() or ""
        return name == DEVICE_NAME
    except Exception:
        # If anything strange in advertisement, ignore it
        return False
# -----------------------------------------------------------------------------
# BLE central workflow
# -----------------------------------------------------------------------------
async def find_wand():
    # Scan for the wand advertisement; return the advertisement (or None)
    try:
        print("Scanning for wand...")
        async with aioble.scan(SCAN_TIMEOUT_MS, interval_us=SCAN_INTERVAL_US,
                               window_us=SCAN_WINDOW_US, active=True) as scanner:
            async for adv in scanner:
                if _adv_matches(adv):
                    print("Found wand:", adv.device)
                    return adv
        print("Scan complete: wand not found")
        return None
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(202, e)
        return None
async def connect_wand(adv):
    # Attempt to connect to a seen advertisement
    try:
        print("Connecting...")
        conn = await aioble.connect(adv.device, timeout_ms=5000)
        print("Connected:", adv.device)
        return conn
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(203, e)
        return None
async def discover_characteristics(conn):
    # Discover service and its characteristics on the wand
    try:
        svc = await conn.service(SERVICE_UUID)
        imu_raw_char   = await svc.characteristic(IMU_RAW_UUID)
        imu_fused_char = await svc.characteristic(IMU_FUSED_UUID)
        system_char    = await svc.characteristic(SYSTEM_UUID)
        control_char   = await svc.characteristic(CONTROL_UUID)
        return imu_raw_char, imu_fused_char, system_char, control_char
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(204, e)
        return None, None, None, None
async def subscribe_notifications(char):
    # Enable notifications on a given characteristic
    try:
        # aioble client API supports subscribe(notify=True, indicate=False)
        await char.subscribe(notify=True)
        return True
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(205, e)
        return False
# -----------------------------------------------------------------------------
# Receivers for notifications
# -----------------------------------------------------------------------------
async def recv_imu_raw_task(char):
    global imu_raw_latest
    try:
        while True:
            data = await char.notified()  # bytes from notify
            try:
                parsed = decode_imu_raw(data)
                imu_raw_latest = parsed
                await _queue_put_latest(imu_raw_queue, parsed)
            except Exception as e:
                io.signal(206, e)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        io.signal(206, e)
async def recv_imu_fused_task(char):
    global imu_fused_latest
    try:
        while True:
            data = await char.notified()
            try:
                parsed = decode_imu_fused(data)
                imu_fused_latest = parsed
                await _queue_put_latest(imu_fused_queue, parsed)
            except Exception as e:
                io.signal(207, e)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        io.signal(207, e)
async def recv_system_task(char):
    global system_latest
    try:
        while True:
            data = await char.notified()
            try:
                parsed = decode_system(data)
                system_latest = parsed
                await _queue_put_latest(system_queue, parsed)
            except Exception as e:
                io.signal(208, e)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        io.signal(208, e)
# -----------------------------------------------------------------------------
# Control commands to wand
# -----------------------------------------------------------------------------
async def wand_set_led_rainbow(control_char):
    # cmd = 1 per wand's handle_control()
    try:
        await control_char.write(b"\x01")
        print("Sent LED rainbow command")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(209, e)
async def wand_reset(control_char):
    # cmd = 2 per wand's handle_control()
    try:
        await control_char.write(b"\x02")
        print("Sent reset command")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        io.signal(209, e)
# -----------------------------------------------------------------------------
# High-level runner: auto-connect, subscribe, receive, reconnect on drop
# -----------------------------------------------------------------------------
async def ble_main():
    while True:
        conn = None
        imu_raw_char = None
        imu_fused_char = None
        system_char = None
        control_char = None
        tasks = []
        try:
            # Find and connect
            adv = await find_wand()
            if adv is None:
                await asyncio.sleep(RECONNECT_DELAY_S)
                continue
            conn = await connect_wand(adv)
            if conn is None:
                await asyncio.sleep(RECONNECT_DELAY_S)
                continue
            # Optionally negotiate MTU (aioble may auto-negotiate)
            # try:
            #     await conn.exchange_mtu(96)
            # except Exception:
            #     pass
            # Discover chars
            imu_raw_char, imu_fused_char, system_char, control_char = await discover_characteristics(conn)
            if not all([imu_raw_char, imu_fused_char, system_char, control_char]):
                print("Characteristic discovery failed; disconnecting")
                await conn.disconnect()
                await asyncio.sleep(RECONNECT_DELAY_S)
                continue
            # Subscribe to notifications
            ok1 = await subscribe_notifications(imu_raw_char)
            ok2 = await subscribe_notifications(imu_fused_char)
            ok3 = await subscribe_notifications(system_char)
            if not (ok1 and ok2 and ok3):
                print("Subscription failed; disconnecting")
                await conn.disconnect()
                await asyncio.sleep(RECONNECT_DELAY_S)
                continue
            # Start receiver tasks
            t1 = asyncio.create_task(recv_imu_raw_task(imu_raw_char))
            t2 = asyncio.create_task(recv_imu_fused_task(imu_fused_char))
            t3 = asyncio.create_task(recv_system_task(system_char))
            tasks = [t1, t2, t3]
            print("Dock subscribed. Awaiting disconnect or tasks...")
            # Wait for disconnection
            await conn.disconnected()
        except asyncio.CancelledError:
            # Graceful shutdown requested
            break
        except Exception as e:
            io.signal(210, e)
        finally:
            # Cleanup
            for t in tasks:
                try:
                    t.cancel()
                except Exception:
                    pass
            for t in tasks:
                try:
                    await t
                except Exception:
                    pass
            try:
                if conn is not None:
                    await conn.disconnect()
            except Exception:
                pass
            # Small backoff before retry
            await asyncio.sleep(RECONNECT_DELAY_S)
# -----------------------------------------------------------------------------
# Example utility tasks for consuming data (optional)
# -----------------------------------------------------------------------------
async def print_status_task():
    # Periodically print latest system/IMU info
    while True:
        try:
            await asyncio.sleep(1.0)
            if system_latest is not None:
                ts, batt_v, batt_pct, flags = system_latest
                print("System:", {"ts": ts, "batt_v": batt_v, "batt_pct": batt_pct, "flags": flags})
            if imu_fused_latest is not None:
                ts, qw, qx, qy, qz = imu_fused_latest
                print("Fused:", {"ts": ts, "qw": qw, "qx": qx, "qy": qy, "qz": qz})
        except asyncio.CancelledError:
            break
        except Exception as e:
            io.signal(211, e)
# -----------------------------------------------------------------------------
# Entrypoint helpers
# -----------------------------------------------------------------------------
async def main():
    # Launch BLE central and optional status printer
    t_ble = asyncio.create_task(ble_main())
    t_print = asyncio.create_task(print_status_task())
    try:
        await t_ble
    finally:
        t_print.cancel()
        try:
            await t_print
        except Exception:
            pass
def run():
    try:
        asyncio.run(main())
    except Exception as e:
        io.signal(212, e)



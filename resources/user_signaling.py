# Programmer: Odaisen
# Last update: 07/05/26

import uasyncio as asyncio
from machine import Pin, Signal

# Error codes with attached cause
ERROR_INFO = {
    101: ("Unknown", 1),
    102: ("Startup error", 2),
    103: ("Bluetooth error", 3),
    104: ("IMU error", 4),
    105: ("Battery sensing error", 5),
    106: ("Temperature error", 6),
    107: ("Addressable LED error", 7),
}

# Devices with selected indicator LED
_LED_PINS = {
    "wand": 6,
    "dock": 4
}

_LED_INVERTED = {
    "dock": True,
}

# Module state
_led_cache = {}
_tasks = {}
_device_cache = None
_init = False

# Initializes LED and caches both device and led
def init(device):
    global _init, _device_cache

    pin_num = _LED_PINS.get(device)
    if pin_num is None:
        raise ValueError("Unknown device '{}' or LED pin not set".format(device))

    if _init:
        if device != _device_cache:
            raise RuntimeError("Device '{}' already initialized, cannot switch to {}"
                               .format(_device_cache, device))
        print("io._init() already been run for device: {}".format(device))
        return _led_cache[device]

    if device not in _led_cache:
        invert = _LED_INVERTED.get(device, False)
        pin = Pin(pin_num, mode=Pin.OUT)
        led = Signal(pin, invert=invert)
        try: led.off()
        except Exception: pass
        _led_cache[device] = led

    _device_cache = device
    _init = True
    return _led_cache[device]

# Stops running tasks and turns led off
def stop():
    if not _init:
        return False
    dev = _device_cache
    t = _tasks.pop(dev, None)
    if t:
        try: t.cancel()
        except Exception: pass

    led = _led_cache.get(dev)
    if led:
        try: led.off()
        except Exception: pass

    return True

# Returns info on error code, with security on unknown code
def _parse_error(code):
    try:
        code_int = int(code)
    except (ValueError, TypeError):
        code_int = 101
    if code_int not in ERROR_INFO:
        code_int = 101
    desc, times = ERROR_INFO[code_int]
    return code_int, desc, times

# Called function for error signaling
def signal(error_code, error_msg="", on_ms=500, off_ms=500, gap_ms=1000,
           repeat=False, log=True, log_each_group=False):
    dev = _device_cache
    if not _init or _device_cache not in _led_cache:
        raise ValueError("User signaling not initialized")
    stop()
    try:
        task = asyncio.create_task(
            _signal(dev, error_code, error_msg, on_ms, off_ms, gap_ms,
                    repeat, log, log_each_group)
        )
        _tasks[dev] = task
        return task
    except Exception as e:
        code_int, desc, _ = _parse_error(error_code)
        try:
            print("Failed to start signal task:", e)
            print("Error {} - {}\nOriginal error: {}".format(
                code_int, desc, error_msg))
        except Exception: pass
        return None

# Subtask of signal
async def _signal(dev, code, error, on_ms=500, off_ms=500, gap_ms=1000,
                  repeat=False, log=True, log_each_group=False):
    code_int, desc, times = _parse_error(code)

    if log:
        try:
            print("Error {} - {}\nError info: {}".format(
                code_int, desc, error))
        except Exception: pass

    led = _led_cache.get(dev)
    if led is None: return

    try:
        first = True
        while True:
            if not first and log and log_each_group:
                try:
                    print("Error {} - {} (LED repeating)".format(code_int, desc))
                except Exception: pass

            await blink(led, times, on_ms, off_ms)
            if not repeat: break
            first = False
    except asyncio.CancelledError:
        try:
            led.off()
        except Exception: pass
        raise

# LED blinking task
async def blink(led, times, on_ms=500, off_ms=500):
    try:
        for _ in range(int(times)):
            led.on()
            await asyncio.sleep_ms(on_ms)
            led.off()
            await asyncio.sleep_ms(off_ms)
    except asyncio.CancelledError:
        try:
            led.off()
        except Exception: pass
        raise
    except Exception as e:
        try:
            print("LED blinking failed: ", e)
        except Exception: pass
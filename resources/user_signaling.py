# Programmer: Odaisen
# Last update: 02/05/26

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
_led_cache = {} # Caches LED to not initialize multiple times

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

# Gets LED object and caches it for the selected device
def _get_led(device: str) -> Pin:
    pin_num = _LED_PINS.get(device)
    if pin_num is None:
        raise ValueError("Unknown device '{}' or LED pin not set".format(device))
    invert = _LED_INVERTED.get(device, False)
    led = _led_cache.get(device) # Check if LED is already cached (Prevents pin resets)
    if led is None: # Runs if LED is not cached
        pin = Pin(pin_num, mode=Pin.OUT)
        led = Signal(pin, invert=invert)
        _led_cache[device] = led
    return led

# Called function for error signaling
def signal(error_code, device, error_msg, on_ms=500, off_ms=500, gap_ms=1000,
           repeat=False, log=True, log_each_group=False):
    try:
        led = _get_led(device)
    except Exception as e:
        try:
            print("Signal setup failed:", e, "| Original error:", error_msg)
        except Exception:
            pass
        return None
    try:
        task = asyncio.create_task(_signal(led, error_code, error_msg, on_ms, off_ms, gap_ms,
                                           repeat, log, log_each_group))
        return task
    except Exception as e:
        code_int, desc, times = _parse_error(error_code)
        try:
            print("Subtask of signal failed:", e)
            print("Error {} - {}\nOriginal error: {}".format(
                code_int, desc, error_msg))
        except Exception:
            pass
        return None

# Subtask of signal
async def _signal(led: Pin, code, error, on_ms=500, off_ms=500, gap_ms=1000,
                  repeat=False, log=True, log_each_group=False):
    code_int, desc, times = _parse_error(code)
    if log:
        try:
            print("Error {} - {}\nError info: {}".format(
                code_int, desc, error))
        except Exception:
            pass
    try:
        first = True
        while True:
            if not first and log and log_each_group:
                try:
                    print("Error {} - {} (LED repeating)".format(code_int, desc))
                except Exception:
                    pass
            await blink(led, times, on_ms, off_ms)
            await asyncio.sleep_ms(gap_ms)
            if not repeat:
                break
            first = False
    except asyncio.CancelledError:
        try:
            led.off()
        except Exception:
            pass
        raise

# LED blinking task
async def blink(led: Pin, times, on_ms=500, off_ms=500):
    try:
        for _ in range(times):
            led.on()
            await asyncio.sleep_ms(on_ms)
            led.off()
            await asyncio.sleep_ms(off_ms)
    except asyncio.CancelledError:
        try:
            led.off()
        except Exception:
            pass
        raise
    except Exception as e:
        print("LED blinking failed: ", e)
# Programmer: Odaisen
# Last update: 02/05/26

import uasyncio as asyncio
from machine import Pin
# Error codes:
# 101 - Unknown
# 102 - Startup error
# 103 - Bluetooth error
# 104 - IMU error
# 105 - Battery sensing error
# 106 - Temperature error
ERROR_INFO = {
    101: ("Unknown", 1),
    102: ("Startup error", 2),
    103: ("Bluetooth error", 3),
    104: ("IMU error", 4),
    105: ("Battery sensing error", 5),
    106: ("Temperature error", 6),
}
# Cache LED pins per device so we don’t recreate Pin objects repeatedly.
_LED_PINS = {"wand": 6}
_led_cache = {}
def _parse_error(code):  # Returns code, desc, times with fallback to code 101
    try:
        code_int = int(code)
    except (ValueError, TypeError):
        code_int = 101
    desc, times = ERROR_INFO.get(code_int, ERROR_INFO[101])
    return code_int, desc, times
def _get_led(device: str) -> Pin:
    pin_num = _LED_PINS.get(device)
    if pin_num is None:
        raise ValueError("Unknown device '{}' or LED pin not set".format(device))
    led = _led_cache.get(pin_num)
    if led is None:
        led = Pin(pin_num, mode=Pin.OUT)
        _led_cache[pin_num] = led
    return led
def signal(code, device, error, on_ms=500, off_ms=500, gap_ms=1000,
           repeat=False, log=True, log_each_group=False):
    """
    Fire-and-forget wrapper that schedules blinking of an error pattern.
    Safe to call from non-async code. Returns the created task or None.
    """
    try:
        led = _get_led(device)
    except Exception as e:
        # If LED cannot be resolved, just print.
        try:
            print("Signal setup failed:", e, "| Original error:", error)
        except Exception:
            pass
        return None
    try:
        # This will raise if no event loop is running yet; handle below.
        task = asyncio.create_task(_signal(led, code, device, error, on_ms, off_ms, gap_ms,
                                           repeat, log, log_each_group))
        return task
    except Exception:
        # Likely called before the loop starts; at least log it.
        code_int, desc, times = _parse_error(code)
        try:
            print("Error {} - {} ({} blink{})\nError info: {}".format(
                code_int, desc, times, "" if times == 1 else "s", error))
        except Exception:
            pass
        return None
async def _signal(led: Pin, code, device, error, on_ms=500, off_ms=500, gap_ms=1000,
                  repeat=False, log=True, log_each_group=False):
    """
    Coroutine that actually performs the blinking.
    """
    code_int, desc, times = _parse_error(code)
    if log:
        try:
            print("Error {} - {} ({} blink{})\nError info: {}".format(
                code_int, desc, times, "" if times == 1 else "s", error))
        except Exception:
            pass
    try:
        first = True
        while True:
            if not first and log and log_each_group:
                try:
                    print("Error {} - {} (repeating)".format(code_int, desc))
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
async def blink(led: Pin, times, on_ms=500, off_ms=500):  # Blink x times
    on = getattr(led, "on", None)
    off = getattr(led, "off", None)
    if on is None or off is None:
        # Fallback for ports lacking on/off helpers
        for _ in range(times):
            led.value(1)
            await asyncio.sleep_ms(on_ms)
            led.value(0)
            await asyncio.sleep_ms(off_ms)
        return
    for _ in range(times):
        on()
        await asyncio.sleep_ms(on_ms)
        off()
        await asyncio.sleep_ms(off_ms)
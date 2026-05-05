# Programmer: Justin
# Last Update: 02/05/26

# =========================
# IMPORTS
# =========================

import uasyncio as asyncio
#import time
from time import sleep
from machine import Pin, Signal#, I2C

try:
    import resources.user_signaling as io
except Exception as e:
    print("IO import error: ", e)


#code from here on out
try:
    led4      = Signal(Pin(4, Pin.OUT), invert=True)
    led5      = Signal(Pin(5, Pin.OUT), invert=True)
    led6      = Signal(Pin(6, Pin.OUT), invert=True)
    led7      = Signal(Pin(7, Pin.OUT), invert=True)
except Exception as e:
    io.signal(102, "dock", e)
"""
# Direct Pin control - active LOW (LOW = LED ON)
led4 = Pin(4, Pin.OUT)  # Power LED - should be GPIO4
led5 = Pin(5, Pin.OUT)
led6 = Pin(6, Pin.OUT)
led7 = Pin(7, Pin.OUT)
"""

async def test_leds():
    print("Testing all 4 LEDs one by one...")

    # Turn all OFF first (HIGH = off for active-low)
    for p in [led4, led5, led6, led7]:
        p.value(0)

    await asyncio.sleep(1)

    # Test each LED individually
    for i, led in enumerate([led4, led5, led6, led7], 4):
        print(f"Turning ON GPIO {i}")
        led.value(1)  # HIGH = ON
        await asyncio.sleep(2)
        led.value(0)  # LOW = OFF
        await asyncio.sleep(0.5) # It is like this now since they're inverted values baseline

    print("Individual test finished. Now cycling all...")

    counter = 0
    accounting = True
    while accounting:

        # Binary count on the other three LEDs
        led5.value(counter & 1)
        led6.value((counter >> 1) & 1)
        led7.value((counter >> 2) & 1)

        counter = (counter + 1) % 8
        print("number is,",counter)
        await asyncio.sleep(0.4)  # non-bl
        if accounting > 20:
            accounting = False


async def main():
    await test_leds()  # ← put this at the start
    while True:
        led4.value(1)  # or led.value(1)
        sleep(0.2)
        led4.value(0)  # or led.value(0)
        sleep(0.2)
        print("do other leds work?")
        led5.value(1)
        sleep(0.2)
        led5.value(0)
        sleep(0.2)
        led6.value(1)
        sleep(0.2)
        led6.value(0)
        sleep(0.2)
        led7.value(1)
        sleep(0.2)
        led7.value(0)
        sleep(0.2)




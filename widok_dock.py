# Programmer: Justin
# Last Update: 02/05/26

# =========================
# IMPORTS
# =========================

import uasyncio as asyncio
#import time
from time import sleep
from machine import Pin, Signal#, I2C

#code from here on out

led1      = Signal(Pin(5, Pin.OUT), invert=True)
led2      = Signal(Pin(6, Pin.OUT), invert=True)
led3      = Signal(Pin(7, Pin.OUT), invert=True)

async def leds_startup_test():
    led1.on()
    led2.on()
    led3.on()
    await asyncio.sleep(2)

    counter = 0
    accounting = True
    while accounting:

        # Binary count on the other three LEDs
        led1.value(counter & 1)
        led2.value((counter >> 1) & 1)
        led3.value((counter >> 2) & 1)

        counter = (counter + 1) % 8
        await asyncio.sleep(0.4)  # non-bl
        if accounting > 20:
            accounting = False

async def main():
    await leds_startup_test()          # ← add this line

    while True:
        led1.on()  # or led.value(1)
        sleep(0.5)
        led1.off()  # or led.value(0)
        sleep(0.5)


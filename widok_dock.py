# Programmer: Justin
# Last Update: 02/05/26
import time
# =========================
# IMPORTS
# =========================

import uasyncio as asyncio
#import time
from time import sleep
from machine import Pin, Signal#, I2C
import esp32
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
    mos_l = Pin(1, Pin.OUT, value=0)  # GPIO 1 PWM L
    mos_h = Pin(2, Pin.OUT, value=0)  # GPIO 2 PWM H
    test_pin = Pin(1, Pin.OUT) # TODO: remove this later
    rmt_test = esp32.RMT(0, pin=test_pin, clock_div=2)
    #rmt_l = esp32.RMT(1, pin=mos_l, clock_div=80)   #channel 1 maybe swap to 0?
    #rmt_h = esp32.RMT(0, pin=mos_h, clock_div=80)   #channel 0 ask for diff/clarification
    rmt_l = esp32.RMT(0, pin=mos_l, resolution_hz=40_000_000)  # 25 ns resolution
    rmt_h = esp32.RMT(1, pin=mos_h, resolution_hz=40_000_000)

except Exception as e:
    io.signal(102, "dock", e)

charger_task = None

async def ac_drive(freq_hz=50000, duration_ms=30000, dead_us=300):
    """Software-timed half-bridge - low-side first (safe for coil)"""
    period_us = 1_000_000 // freq_hz
    half = period_us // 2

    print(f"Starting charger @ {freq_hz:,} Hz | Dead time: {dead_us} ns | Running for {duration_ms/1000:.1f} s")

    start = time.ticks_ms()
    end = time.ticks_add(start, duration_ms)

    while time.ticks_diff(end, time.ticks_ms()) > 0:
        # 1. Low-side ON first (discharges coil energy)
        mos_l.value(1)
        mos_h.value(0)
        time.sleep_us(half - dead_us)

        # Dead time (both OFF)
        mos_l.value(0)
        mos_h.value(0)
        time.sleep_us(dead_us)

        # 2. High-side ON
        mos_l.value(0)
        mos_h.value(1)
        time.sleep_us(half - dead_us)

        # Dead time again
        mos_l.value(0)
        mos_h.value(0)
        time.sleep_us(dead_us)

    # Safety shutdown
    mos_l.value(0)
    mos_h.value(0)
    print("Charger stopped safely")

def start_charger(freq_hz=50000, duration_ms=30000, dead_us=0.25):
    global charger_task
    if charger_task and not charger_task.done():
        charger_task.cancel()
    charger_task = asyncio.create_task(ac_drive(freq_hz, duration_ms, dead_us))

def stop_charger():
    global charger_task
    if charger_task:
        charger_task.cancel()
    mos_l.value(0)
    mos_h.value(0)
    print("Charger emergency stop")


async def test_leds():
    print("Testing all 4 LEDs one by one...")

    # Turn all OFF first (HIGH = off for active-low)
    for p in [led4, led5, led6, led7]:
        p.value(0)

    await asyncio.sleep(0.1)

    # Test each LED individually
    for i, led in enumerate([led4, led5, led6, led7], 4):
        print(f"Turning ON GPIO {i}")
        led.value(1)  # HIGH = ON
        await asyncio.sleep(0.2)
        led.value(0)  # LOW = OFF
        await asyncio.sleep(0.1) # It is like this now since they're inverted values baseline

    print("Individual test finished. Now cycling all...")

    counter = 0
    countering = 0
    accounting = True
    while accounting:

        # Binary count on the other three LEDs
        led5.value(counter & 1)
        led6.value((counter >> 1) & 1)
        led7.value((counter >> 2) & 1)

        counter = (counter + 1) % 8
        countering = countering + 1
        print("number is,",counter,"(",countering,"lifetime/out of 16)")
        await asyncio.sleep(0.1)  # non-bl
        if countering >= 16:
            accounting = False

async def ac_drive_rmt_1(freq_hz=275000, duration_ms=10000, dead_us=0.2):
    period_ns = 1_000_000_000 / freq_hz
    half_ns = period_ns / 2
    tick_ns = 25
    dead_ticks = int(dead_us * 1000 / tick_ns)
    half_ticks = int(half_ns / tick_ns) - dead_ticks

    print(f"RMT AC drive @ {freq_hz:,} Hz | Dead time: {dead_us} µs")

    # Low-side first complementary pattern
    # (Low-side pattern: high for half, low for half with dead gaps)
    rmt_l.loop(True)
    rmt_h.loop(True)

    # Low-side pattern (high for half - dead, low for dead + half)
    rmt_l.write_pulses((half_ticks, half_ticks + 2*dead_ticks), 1)
    # High-side pattern (opposite, delayed by dead time)
    rmt_h.write_pulses((0, dead_ticks, half_ticks, dead_ticks + half_ticks), 0)

    await asyncio.sleep_ms(duration_ms)

    # Safe stop
    rmt_l.loop(False)
    rmt_h.loop(False)
    rmt_l.write_pulses((0, 0), 0)
    rmt_h.write_pulses((0, 0), 0)
    print("RMT stopped - MOSFETs OFF")
async def ac_drive_rmt(freq_hz=275000, duration_ms=5000, dead_us=0.25):
    """RMT-based half-bridge - low side first"""
    period_ns = 1_000_000_000 // freq_hz
    half_ns = period_ns // 2
    dead_ns = int(dead_us * 1000)
    tick_ns = 25                                 # because resolution_hz=40MHz

    half_ticks = (half_ns - dead_ns) // tick_ns
    dead_ticks = dead_ns // tick_ns

    print(f"RMT Drive @ {freq_hz:,} Hz | Dead time: {dead_us} µs | Duration: {duration_ms} ms")

    # Enable continuous looping
    rmt_l.loop(True)
    rmt_h.loop(True)

    # Low-side pattern: ON for half period, then dead time gaps
    rmt_l.write_pulses((half_ticks, half_ticks + 2 * dead_ticks), start_level=1)

    # High-side pattern: delayed by dead time (opposite phase)
    rmt_h.write_pulses((dead_ticks, half_ticks, dead_ticks + half_ticks), start_level=0)

    # Run for the requested duration
    await asyncio.sleep_ms(duration_ms)

    # Safe shutdown
    rmt_l.loop(False)
    rmt_h.loop(False)
    rmt_l.write_pulses((0, 0), 0)
    rmt_h.write_pulses((0, 0), 0)

    print("RMT stopped - MOSFETs OFF")
async def rmt_simple_test(duration_ms=10000):
    print("RMT Simple Test: 50 kHz square wave on GPIO 1 (10 seconds)")
    print("Probe SW_NODE with multimeter in Frequency or AC Voltage mode")

    # 50 kHz square wave = period 20 µs → 10 µs high / 10 µs low
    # With 25 ns resolution: 10 µs = 400 ticks
    rmt_test.loop_count(-1)                    # infinite loop
    rmt_test.write_pulses((400, 400), 0)       # start low, 400 ticks low + 400 ticks high

    await asyncio.sleep_ms(duration_ms)

    # Stop cleanly
    rmt_test.loop_count(0)
    rmt_test.active(False)
    test_pin.value(0)
    print("Simple RMT test finished")

#can also be run in the background using asyncio.create_task(...)
# invest into that, looking for that

# Sure, for today lets move on and lets keep the finalization of this MOSFET system for tomorrow- now would be a good time to aknowledge the TFT LCD screen, and lets try to access it through our ports. How do we get around this screen and rotary encoder thing? You mentioned it and now i'm really curious and interested in it.
# ^ before going offline prompt copy and paste into the gonk

async def ac_drive(freq_hz=275000, duration_ms=10000, dead_us=200):
    """Safe half-bridge drive - low-side first"""
    period_us = 1_000_000 // freq_hz
    half = period_us // 2

    print(f"AC drive @ {freq_hz:,} Hz | Dead time: {dead_us} ns | Duration: {duration_ms} ms")

    start = time.ticks_ms()
    end = time.ticks_add(start, duration_ms)

    while time.ticks_diff(end, time.ticks_ms()) > 0:
        # 1. Low-side ON first (discharges any residual energy)
        mos_l.value(1)
        mos_h.value(0)
        # time.sleep_us(half - dead_us)
        time.sleep_us(1)

        # Dead time (both OFF - critical!)
        mos_l.value(0)
        mos_h.value(0)
        time.sleep_us(dead_us)

        # 2. High-side ON
        mos_l.value(0)
        mos_h.value(1)
        time.sleep_us(half - dead_us)

        # Dead time again
        mos_l.value(0)
        mos_h.value(0)
        time.sleep_us(dead_us)

    # Safety shutdown
    mos_l.value(0)
    mos_h.value(0)
    print("AC drive finished - MOSFETs OFF")
""" this one is really good though so watch out maybe use this after all- needs irl testing anyways.
async def ac_drive_rmt(freq_hz=275000, duration_ms=2000, dead_us=25):
    #High-frequency half-bridge using RMT - best for 275 kHz
    period_us = 1_000_000 / freq_hz
    half_period = int(period_us / 2)
    dead_ticks = dead_us                     # resolution is ~1 µs with clock_div=80

    print(f"RMT AC drive @ {freq_hz:,} Hz | Dead time: {dead_us} µs | Duration: {duration_ms} ms")

    # Pulse pattern: [High-side ON time, Dead, Low-side ON time, Dead]
    pulses_h = (half_period - dead_ticks, dead_ticks, 0, dead_ticks)          # High-side pattern
    pulses_l = (0, dead_ticks, half_period - dead_ticks, dead_ticks)          # Low-side pattern

    # Enable continuous looping
    rmt_h.loop(True)
    rmt_l.loop(True)

    rmt_h.write_pulses(pulses_h, 1)   # 1 = start level HIGH for high-side
    rmt_l.write_pulses(pulses_l, 0)   # 0 = start level LOW for low-side

    await asyncio.sleep_ms(duration_ms)

    # Stop safely
    rmt_h.loop(False)
    rmt_l.loop(False)
    rmt_h.write_pulses((0, 0), 0)
    rmt_l.write_pulses((0, 0), 0)

    print("RMT AC drive stopped - MOSFETs OFF")
"""
def stop_mosfets():
    rmt_h.loop(False)
    rmt_l.loop(False)
    mos_h.value(0)
    mos_l.value(0)
    print("MOSFETS stopped - MOSFETs OFF")

async def main():
    await test_leds()  # ← put this at the start
    # Test the coil safely
    #await ac_drive_rmt(275000,30000, 25)  # target frequency of 275 kHz
    #await ac_drive_rmt(freq_hz=50000, duration_ms=10000, dead_us=0.5) # 50 khz 10 seconds
    #await rmt_simple_test()
    #start_charger(freq_hz=50000, duration_ms=30000, dead_us=300) # 50 kHz for 30 seconds
    await ac_drive(275000,30000,0.2) #testing this ughhhh
    # Or run it in background:
    # asyncio.create_task(ac_drive_rmt(...))
    #await ac_drive_rmt(freq_hz=275000, duration_ms=10000, dead_us=0.2)  # 10 seconds @ 275 kHz and at 200 ns dead time

    # You can now do other things here (encoder, temp, GUI...)
    #while True:
        # Example: read encoder, update LCD, check temp, etc.
    #    await asyncio.sleep_ms(100)  # your main loop speed

        # Optional: stop charger after some time
        # if some_condition:
        #     charger_task.cancel()
        #     break

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




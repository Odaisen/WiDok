# Programmer: Justin
# Last Update: 02/05/26

# =========================
# IMPORTS
# =========================
import machine
import time
import uasyncio as asyncio
import resources.bluetooth_protocol_dock as ble_dock
#import time
from time import sleep
from machine import Pin, Signal#, I2C
import esp32
import uctypes
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
    pin_pwm_l = Pin(1, Pin.OUT)
    pin_pwn_h = Pin(2, Pin.OUT)
    # maybe i can move this down- dependssssss
    pin_pwm_l.value(0)
    pin_pwn_h.value(0)

    """
    p_test = Pin(2, Pin.OUT) #todo delete when test done
    #todo try to take this out soon
    mos_l= Pin(1, Pin.OUT)
    mos_h = Pin(2, Pin.OUT)
    rmt_l = esp32.RMT(0, pin=mos_l, clock_div=2)  # 25 ns resolution
    rmt_h = esp32.RMT(1, pin=mos_h, clock_div=2)
    """
except Exception as e:
    io.signal(102, "dock", e)


# Consume system data (battery, flags)
async def system_consumer():
    while True:
        try:
            ts, batt_v, batt_pct, flags = await ble_dock.system_queue.get()
            print("SYSTEM:", ts, "V=", batt_v, "pct=", batt_pct, "flags=", flags)
            if batt_pct <= 15:
                print("Warning: Low battery on wand!")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print("system_consumer error:", e)
# If you want a very light setup, you can skip the above consumers and rely on:
# - ble_dock.system_latest
# - ble_dock.imu_fused_latest
# - ble_dock.imu_raw_latest
# polled on a timer/task. The queue-based approach is better for streaming.






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

def stop_mosfets():
    rmt_h.loop(False)
    rmt_l.loop(False)
    mos_h.value(0)
    mos_l.value(0)
    print("MOSFETS stopped - MOSFETs OFF")

def led_loops():
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

async def ac_drive_rmt_275khz(duration_ms=100000, dead_ns=250):
    print(f"RMT Half-Bridge @ 275 kHz | Dead time: {dead_ns} ns | Duration: {duration_ms} ms")

    # Timing calculations (25 ns per tick)
    period_ns = 1_000_000_000 // 275000
    half_ticks = (period_ns // 2 - dead_ns) // 25
    dead_ticks = dead_ns // 25

    rmt_l.loop_count(-1)
    rmt_h.loop_count(-1)

    # Low-side first pattern
    rmt_l.write_pulses((half_ticks, half_ticks + 2*dead_ticks), 1)
    # High-side delayed pattern
    rmt_h.write_pulses((dead_ticks, half_ticks, dead_ticks + half_ticks), 0)

    await asyncio.sleep_ms(duration_ms)

    # Safe stop
    rmt_l.loop_count(0)
    rmt_h.loop_count(0)
    rmt_l.active(False)
    rmt_h.active(False)
    mos_l.value(0)
    mos_h.value(0)
    print("275 kHz RMT drive stopped safely")

"claude defs"

def start_bridge(freq=200000):
    # Deinit cleanly first in case of previous state
    try:
        machine.PWM(Pin(2)).deinit()
        machine.PWM(Pin(1)).deinit()
    except:
        pass
    time.sleep_ms(10)

# Start PWM_L first
    pwm_l = machine.PWM(Pin(1), freq=freq, duty_u16=32768)  # 50%

    # Small delay before starting PWM_H
    # This gives a crude but real dead time at startup
    time.sleep_us(10)

    # PWM_H — same frequency, same duty
    # LEDC cannot invert so we rely on the hardware
    # RC network (R28/R29 + C22/C23) to create
    # the complementary behaviour at the gate driver
    pwm_h = machine.PWM(Pin(2), freq=freq, duty_u16=32768)  # 50%

    print("PWM_L freq:", pwm_l.freq())
    print("PWM_H freq:", pwm_h.freq())
    return pwm_h, pwm_l

def stop_bridge(pwm_h, pwm_l):
    pwm_h.duty_u16(0)
    pwm_l.duty_u16(0)
    time.sleep_ms(1)
    pwm_h.deinit()
    pwm_l.deinit()
    # Drive pins LOW explicitly after deinit
    Pin(2, Pin.OUT).value(0)
    Pin(1, Pin.OUT).value(0)
    print("Bridge stopped")

def stop_pwm_h(pwm_h):
    pwm_h.duty_u16(0)
    time.sleep_ms(1)
    pwm_h.deinit()
    Pin(2, Pin.OUT).value(0)

# IO_MUX base for GPIO1 and GPIO2
# Drive strength bits [11:10] in IO_MUX register
IO_MUX_BASE = 0x60009000

#todo delete this segment if it's all just bs!!!!
def set_drive_strength(gpio_num, strength):
    # Each GPIO has a 4-byte register offset from base
    reg_addr = IO_MUX_BASE + (gpio_num + 1) * 4
    reg = uctypes.struct(reg_addr, {"val": uctypes.UINT32 | 0}, uctypes.LITTLE_ENDIAN)
    # Clear bits 11:10 then set drive strength
    reg.val = (reg.val & ~(0x3 << 10)) | ((strength & 0x3) << 10)
"""
set_drive_strength(1, 3)  # GPIO1 max drive
set_drive_strength(2, 3)  # GPIO2 max drive
"""


async def main():
    #await test_leds()  # ← put this at the start

    #todo take this away if claus method works better
    #await ac_drive_rmt_(freq_hz=50000, duration_ms=50000, dead_us=0.2) # 50 khz 50 seconds
    #await ac_drive_rmt_275khz() # 100 seconds or smth
    testing_low_khz = True
    "claude segment"

    low_khz = 3000
    two_hundred_khz = 200000
    ultra_low_khz = 10
    # off for now testing etc etc
    # pwm_h, pwm_l = start_bridge(two_hundred_khz)
    if testing_low_khz:
        pwm_h = machine.PWM(Pin(2), freq=two_hundred_khz, duty_u16=32768)
        time.sleep_us(10)
        pwm_l = machine.PWM(Pin(1), freq=two_hundred_khz, duty_u16=32768)
        #stop_pwm_h(pwm_h)
    #pin_pwm_l.value(1)
    print("pwm stuff done?")

    # Start BLE client in the background
    asyncio.create_task(ble_client_main())

    # Your normal main loop (still runs everything else)
    while True:
        # Example: every 5 seconds send a test command
        # await send_command(1)   # rainbow LEDs on host
        await asyncio.sleep_ms(50)


    while False:
        p_test.value(1)
        time.sleep_ms(500)
        p_test.value(0)
        time.sleep_ms(500)
        #led_loops()




# Programmer : Odaisen
# Last update: 05/05/2026

import uasyncio as asyncio
from machine import Pin
import neopixel

'''
Modes:
Solid
Breathe
Chase
Rainbow
'''

_ADDR_LED_PINS = {
    "wand": (8, 18),   # IO8=DI, IO18=BI
    "dock": (0, 0),    # placeholder
}
_DEFAULT_DEVICE = "wand"
_DEFAULT_SEGMENTS = 1
_DEFAULT_LEDS_PER_SEG = 20
_DEFAULT_BRIGHTNESS = 0.15
_ENABLE_GAMMA = True
def _build_gamma(gamma=2.2):
    lut = bytearray(256)
    for i in range(256):
        lut[i] = int((i / 255.0) ** gamma * 255 + 0.5)
    return lut
_GAMMA = _build_gamma() if _ENABLE_GAMMA else None
def _scale_color(rgb, brightness):
    r, g, b = int(rgb[0]) & 255, int(rgb[1]) & 255, int(rgb[2]) & 255
    if _GAMMA:
        r, g, b = _GAMMA[r], _GAMMA[g], _GAMMA[b]
    if brightness < 1.0:
        br = brightness
        r = int(r * br)
        g = int(g * br)
        b = int(b * br)
    if r > 255: r = 255
    if g > 255: g = 255
    if b > 255: b = 255
    return (r, g, b)
def _wheel(pos):
    pos = 255 - (pos & 255)
    if pos < 85:
        return (255 - pos * 3, 0, pos * 3)
    if pos < 170:
        pos -= 85
        return (0, pos * 3, 255 - pos * 3)
    pos -= 170
    return (pos * 3, 255 - pos * 3, 0)
def _get_device_pins(device):
    pins = _ADDR_LED_PINS.get(device)
    if not pins:
        raise ValueError("Unknown device '{}' or LED pins not set".format(device))
    return int(pins[0]), int(pins[1])
class _WS281xController:
    def __init__(self, total_leds, di_pin, bi_pin, brightness):
        self.total = int(total_leds)
        if self.total <= 0:
            raise ValueError("Total LEDs must be > 0")
        self.di_pin = int(di_pin)
        self.bi_pin = int(bi_pin)
        self.brightness = max(0.0, min(1.0, float(brightness)))
        self._use_bi = (self.bi_pin not in (None, 0)) and (self.bi_pin != self.di_pin)
        self.np_di = neopixel.NeoPixel(Pin(self.di_pin, Pin.OUT), self.total, bpp=3)
        self.np_bi = None
        if self._use_bi:
            self.np_bi = neopixel.NeoPixel(Pin(self.bi_pin, Pin.OUT), self.total, bpp=3)
        # Mode state
        self._mode = "breathe"
        self._mode_params = {"color": (0, 64, 128), "period_ms": 1800}
        # Internal animation state
        self._tick = 0          # generic frame counter
        self._rainbow_off = 0   # rainbow offset
    # --------------- Configuration ---------------
    def set_brightness(self, value):
        self.brightness = max(0.0, min(1.0, float(value)))
    def set_mode(self, name, **params):
        self._mode = str(name)
        self._mode_params = dict(params)
        # reset internal counters on mode change
        self._tick = 0
        if self._mode == "rainbow":
            self._rainbow_off = 0
    # --------------- Low-level drawing ---------------
    def _fill_both(self, color):
        c = _scale_color(color, self.brightness)
        self.np_di.fill(c)
        if self._use_bi:
            self.np_bi.fill(c)
    def _set_both(self, i, color):
        c = _scale_color(color, self.brightness)
        self.np_di[i] = c
        if self._use_bi:
            self.np_bi[i] = c
    def _write_both(self):
        self.np_di.write()
        if self._use_bi:
            self.np_bi.write()
    # --------------- Pattern steps (one frame) ---------------
    async def _step_off(self):
        self._fill_both((0, 0, 0))
        self._write_both()
        await asyncio.sleep_ms(80)
    async def _step_solid(self, color=(16, 16, 16)):
        self._fill_both(color)
        self._write_both()
        await asyncio.sleep_ms(80)
    async def _step_breathe(self, color=(0, 64, 128), period_ms=1800):
        steps = 60  # frames per cycle
        self._tick = (self._tick + 1) % steps
        phase = self._tick / (steps - 1)
        # ease in/out
        if phase < 0.5:
            y = 2 * phase * phase
        else:
            y = 1 - 2 * (1 - phase) * (1 - phase)
        env = 0.15 + 0.85 * y
        c = (int(color[0] * env), int(color[1] * env), int(color[2] * env))
        self._fill_both(c)
        self._write_both()
        dt = max(10, int(period_ms) // steps)
        await asyncio.sleep_ms(dt)
    async def _step_chase(self, color=(255, 160, 32), tail=12, step_ms=25):
        total = self.total
        if total <= 0:
            await asyncio.sleep_ms(step_ms)
            return
        self._tick = (self._tick + 1) % total
        head = self._tick
        tail = max(1, int(tail))
        # clear
        for i in range(total):
            self._set_both(i, (0, 0, 0))
        # draw tail with linear fade
        for t in range(tail):
            idx = (head - t) % total
            s = int(255 * (1 - t / tail))
            self._set_both(idx, (color[0] * s // 255, color[1] * s // 255, color[2] * s // 255))
        self._write_both()
        await asyncio.sleep_ms(int(step_ms))
    async def _step_rainbow(self, cycle_ms=4000):
        frame_dt = 33  # ~30 fps
        off = self._rainbow_off
        total = self.total
        for i in range(total):
            pos = (i * 256 // total + off) & 255
            self.np_di[i] = _scale_color(_wheel(pos), self.brightness)
            if self._use_bi:
                self.np_bi[i] = self.np_di[i]
        self._write_both()
        # advance offset
        self._rainbow_off = (off + 256 * frame_dt // max(1, int(cycle_ms))) & 255
        await asyncio.sleep_ms(frame_dt)
    # --------------- Main update loop ---------------
    async def run(self):
        while True:
            try:
                m = self._mode
                p = self._mode_params
                if m == "off":
                    await self._step_off()
                elif m == "solid":
                    await self._step_solid(p.get("color", (16, 16, 16)))
                elif m == "breathe":
                    await self._step_breathe(color=p.get("color", (0, 64, 128)),
                                             period_ms=int(p.get("period_ms", 1800)))
                elif m == "chase":
                    await self._step_chase(color=p.get("color", (255, 160, 32)),
                                           tail=int(p.get("tail", 12)),
                                           step_ms=int(p.get("step_ms", 25)))
                elif m == "rainbow":
                    await self._step_rainbow(cycle_ms=int(p.get("cycle_ms", 4000)))
                else:
                    # unknown mode: turn off softly
                    await self._step_off()
            except asyncio.CancelledError:
                # ensure off on cancel
                try:
                    self._fill_both((0, 0, 0))
                    self._write_both()
                except Exception:
                    pass
                raise
            except Exception:
                # brief pause on unexpected error, keep running
                await asyncio.sleep_ms(50)
# -----------------------
# Module-level interface
# -----------------------
_strip = None
_total_leds = 0
def init(device=_DEFAULT_DEVICE, segments=_DEFAULT_SEGMENTS, leds_per_segment=_DEFAULT_LEDS_PER_SEG,
         brightness=_DEFAULT_BRIGHTNESS, di=None, bi=None):
    """
    Initialize the strip.
    - device: key from _ADDR_LED_PINS to get (di, bi) pins, unless di/bi override is provided
    - segments * leds_per_segment = total LED count
    """
    global _strip, _total_leds
    try:
        if di is None or bi is None:
            di_pin, bi_pin = _get_device_pins(device)
        else:
            di_pin, bi_pin = int(di), int(bi)
        total = int(segments) * int(leds_per_segment)
        _strip = _WS281xController(total_leds=total, di_pin=di_pin, bi_pin=bi_pin, brightness=brightness)
        _total_leds = total
        return _strip
    except Exception as e:
        print("addr_leds init failed:", e)
        _strip = None
        _total_leds = 0
        return None
def set_mode(name, **params):
    s = _strip
    if s:
        s.set_mode(name, **params)
def set_brightness(value):
    s = _strip
    if s:
        s.set_brightness(value)
async def run():
    s = _strip
    if s is None:
        # Keep yielding so task can be scheduled even if not initialized
        while True:
            await asyncio.sleep_ms(1000)
    await s.run()
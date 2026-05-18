# Programmer: the claud and justin
# WiDok-Dock V1.0 — Display & UI
# ST7735 128x160, SPI + Rotary Encoder
# Last Update: 08/05/26

import machine
import st7735
import framebuf
import uasyncio as asyncio
import time

# ── Pin definitions ────────────────────────────────────────────────────────
SPI_SCL     = 9
SPI_SDA     = 10
PIN_RES     = 11
PIN_DC      = 12
PIN_CS      = 13
PIN_BLK     = 14

ROT_A       = 42
ROT_B       = 41
ROT_D       = 40   # push button / click

# ── Display init ───────────────────────────────────────────────────────────
spi = machine.SPI(
    1,
    baudrate=20_000_000,
    polarity=0,
    phase=0,
    sck=machine.Pin(SPI_SCL),
    mosi=machine.Pin(SPI_SDA)
)

display = st7735.st7735(
    spi,
    rst=machine.Pin(PIN_RES),
    dc=machine.Pin(PIN_DC),
    cs=machine.Pin(PIN_CS),
    width=128,
    height=160
)

# Backlight on
backlight = machine.Pin(PIN_BLK, machine.Pin.OUT)
backlight.value(1)

# ── Colours (RGB565) ───────────────────────────────────────────────────────
BLACK   = 0x0000
WHITE   = 0xFFFF
CYAN    = 0x07FF
GREEN   = 0x07E0
RED     = 0xF800
YELLOW  = 0xFFE0
GREY    = 0x8410
DKGREY  = 0x2104

# ── Shared state ───────────────────────────────────────────────────────────
# These get updated by BLE client when connected
ble_state = {
    "connected":    False,
    "battery_v":    0.0,
    "battery_pct":  0,
    "imu_ax":       0.0,
    "imu_ay":       0.0,
    "imu_az":       0.0,
    "charging":     False,
}

# ── Rotary encoder ─────────────────────────────────────────────────────────
class RotaryEncoder:
    def __init__(self, pin_a, pin_b, pin_d):
        self.a      = machine.Pin(pin_a, machine.Pin.IN, machine.Pin.PULL_UP)
        self.b      = machine.Pin(pin_b, machine.Pin.IN, machine.Pin.PULL_UP)
        self.btn    = machine.Pin(pin_d, machine.Pin.IN, machine.Pin.PULL_UP)
        self._pos   = 0
        self._last_a = self.a.value()
        self._btn_last = 1
        self._btn_pressed = False
        self._delta = 0    # +1 or -1 pending consumption

    def update(self):
        # Read rotation
        a_val = self.a.value()
        if a_val != self._last_a:
            if self.b.value() != a_val:
                self._delta = 1
            else:
                self._delta = -1
            self._pos += self._delta
        self._last_a = a_val

        # Read button (falling edge = press)
        btn_now = self.btn.value()
        if self._btn_last == 1 and btn_now == 0:
            self._btn_pressed = True
        self._btn_last = btn_now

    def get_delta(self):
        d = self._delta
        self._delta = 0
        return d

    def get_press(self):
        p = self._btn_pressed
        self._btn_pressed = False
        return p

encoder = RotaryEncoder(ROT_A, ROT_B, ROT_D)

# ── Menu definition ────────────────────────────────────────────────────────
MENU_ITEMS = [
    "Status",
    "Charging",
    "IMU Data",
    "BLE Info",
    "Settings",
]

# ── UI state machine ───────────────────────────────────────────────────────
class UI:
    # Screens
    SCREEN_STATUS   = 0
    SCREEN_MENU     = 1
    SCREEN_CHARGING = 2
    SCREEN_IMU      = 3
    SCREEN_BLE      = 4
    SCREEN_SETTINGS = 5

    def __init__(self):
        self.screen         = self.SCREEN_STATUS
        self.menu_index     = 0
        self.needs_redraw   = True
        self._last_screen   = -1

    def navigate(self, delta):
        if self.screen == self.SCREEN_MENU:
            self.menu_index = (self.menu_index + delta) % len(MENU_ITEMS)
            self.needs_redraw = True

    def select(self):
        if self.screen == self.SCREEN_STATUS:
            # Click on status goes to menu
            self.screen = self.SCREEN_MENU
            self.needs_redraw = True

        elif self.screen == self.SCREEN_MENU:
            # Map menu index to screen
            mapping = {
                0: self.SCREEN_STATUS,
                1: self.SCREEN_CHARGING,
                2: self.SCREEN_IMU,
                3: self.SCREEN_BLE,
                4: self.SCREEN_SETTINGS,
            }
            self.screen = mapping.get(self.menu_index, self.SCREEN_STATUS)
            self.needs_redraw = True

        else:
            # Any other screen — click goes back to menu
            self.screen = self.SCREEN_MENU
            self.needs_redraw = True

    def mark_dirty(self):
        self.needs_redraw = True

ui = UI()

# ── Drawing helpers ────────────────────────────────────────────────────────
def draw_header(title, colour=CYAN):
    display.fill_rect(0, 0, 128, 18, colour)
    display.text(title, 4, 4, BLACK)

def draw_footer(hint, colour=DKGREY):
    display.fill_rect(0, 148, 128, 12, colour)
    display.text(hint, 2, 149, GREY)

def draw_hline(y, colour=DKGREY):
    display.hline(0, y, 128, colour)

def ble_dot():
    return GREEN if ble_state["connected"] else RED

def battery_colour(pct):
    if pct > 50:    return GREEN
    if pct > 20:    return YELLOW
    return RED

# ── Screen renderers ───────────────────────────────────────────────────────
def draw_status():
    display.fill(BLACK)
    draw_header("WiDok-Dock")

    # BLE connection status
    connected = ble_state["connected"]
    display.text("BLE:", 4, 26, WHITE)
    status_text = "Connected   " if connected else "Searching..."
    status_col  = GREEN if connected else YELLOW
    display.text(status_text, 36, 26, status_col)

    draw_hline(38)

    # Battery
    pct = ble_state["battery_pct"]
    v   = ble_state["battery_v"]
    display.text("Wand Bat:", 4, 44, WHITE)
    display.text(f"{pct}%", 80, 44, battery_colour(pct))
    display.text(f"{v:.2f}V", 4, 56, GREY)

    # Battery bar
    bar_w = int((pct / 100) * 100)
    display.fill_rect(4, 68, 100, 8, DKGREY)
    display.fill_rect(4, 68, bar_w, 8, battery_colour(pct))
    display.rect(4, 68, 100, 8, WHITE)

    draw_hline(82)

    # Charging state
    charging = ble_state["charging"]
    display.text("Charging:", 4, 88, WHITE)
    display.text("ON " if charging else "OFF", 80, 88, GREEN if charging else GREY)

    draw_hline(100)

    # Low battery warning
    if pct < 20 and pct > 0:
        display.fill_rect(4, 106, 120, 14, RED)
        display.text("LOW BATTERY!", 8, 108, WHITE)

    draw_footer("Click=Menu")

def draw_menu():
    display.fill(BLACK)
    draw_header("Menu", CYAN)

    item_h = 22
    visible = 5  # fits on screen

    for i, item in enumerate(MENU_ITEMS):
        y = 22 + i * item_h
        if i == ui.menu_index:
            display.fill_rect(0, y, 128, item_h - 2, CYAN)
            display.text("> " + item, 4, y + 5, BLACK)
        else:
            display.text("  " + item, 4, y + 5, WHITE)

    draw_footer("Turn=Nav  Click=OK")

def draw_charging():
    display.fill(BLACK)
    draw_header("Charging", GREEN)

    charging = ble_state["charging"]
    pct = ble_state["battery_pct"]

    display.text("Status:", 4, 26, WHITE)
    display.text("ACTIVE" if charging else "IDLE", 60, 26, GREEN if charging else GREY)

    draw_hline(38)

    display.text("Wand battery:", 4, 46, WHITE)
    display.text(f"{pct}%", 4, 58, battery_colour(pct))

    # Big battery bar
    bar_w = int((pct / 100) * 116)
    display.fill_rect(4, 72, 116, 16, DKGREY)
    display.fill_rect(4, 72, bar_w, 16, battery_colour(pct))
    display.rect(4, 72, 116, 16, WHITE)

    draw_hline(96)

    if pct >= 95:
        display.fill_rect(4, 102, 120, 14, GREEN)
        display.text("Fully charged!", 6, 104, BLACK)
    elif pct < 20:
        display.fill_rect(4, 102, 120, 14, RED)
        display.text("Low — charge now", 4, 104, WHITE)

    draw_footer("Click=Back")

def draw_imu():
    display.fill(BLACK)
    draw_header("IMU Data", YELLOW)

    ax = ble_state["imu_ax"]
    ay = ble_state["imu_ay"]
    az = ble_state["imu_az"]

    display.text("Accelerometer:", 4, 24, YELLOW)
    display.text(f"X: {ax:+.3f}", 4, 38, WHITE)
    display.text(f"Y: {ay:+.3f}", 4, 50, WHITE)
    display.text(f"Z: {az:+.3f}", 4, 62, WHITE)

    draw_hline(76)

    display.text("(IMU offline)", 4, 84, GREY)
    display.text("Values show 0.0", 4, 96, GREY)
    display.text("until IMU works", 4, 108, GREY)

    draw_footer("Click=Back")

def draw_ble():
    display.fill(BLACK)
    draw_header("BLE Info", CYAN)

    connected = ble_state["connected"]

    display.text("Device:", 4, 24, WHITE)
    display.text("WiDok-Wand", 4, 36, CYAN)

    draw_hline(50)

    display.text("State:", 4, 58, WHITE)
    display.text(
        "Connected" if connected else "Disconnected",
        4, 70,
        GREEN if connected else RED
    )

    draw_hline(84)

    display.text("MTU: 96", 4, 92, GREY)
    display.text("Protocol: BLE", 4, 104, GREY)
    display.text("Lib: aioble", 4, 116, GREY)

    draw_footer("Click=Back")

def draw_settings():
    display.fill(BLACK)
    draw_header("Settings", GREY)

    display.text("Freq target:", 4, 26, WHITE)
    display.text("275 kHz", 80, 26, CYAN)

    draw_hline(38)

    display.text("Dead time:", 4, 46, WHITE)
    display.text("56 ns", 80, 46, CYAN)

    draw_hline(58)

    display.text("BLE MTU:", 4, 66, WHITE)
    display.text("96", 80, 66, CYAN)

    draw_hline(78)

    display.text("FW version:", 4, 86, WHITE)
    display.text("V1.0", 80, 86, CYAN)

    draw_footer("Click=Back")

# ── Screen dispatch ────────────────────────────────────────────────────────
def render():
    s = ui.screen
    if   s == UI.SCREEN_STATUS:   draw_status()
    elif s == UI.SCREEN_MENU:     draw_menu()
    elif s == UI.SCREEN_CHARGING: draw_charging()
    elif s == UI.SCREEN_IMU:      draw_imu()
    elif s == UI.SCREEN_BLE:      draw_ble()
    elif s == UI.SCREEN_SETTINGS: draw_settings()
    ui.needs_redraw = False

# ── Main UI loop ───────────────────────────────────────────────────────────
async def ui_loop():
    # Initial draw
    render()

    while True:
        encoder.update()

        delta = encoder.get_delta()
        if delta != 0:
            ui.navigate(delta)

        if encoder.get_press():
            ui.select()

        if ui.needs_redraw:
            render()

        # Status screen auto-refreshes every 2 seconds
        # to show updated BLE/battery data
        if ui.screen == UI.SCREEN_STATUS:
            ui.mark_dirty()
            await asyncio.sleep_ms(2000)
        else:
            await asyncio.sleep_ms(50)
"""
# ── Entry point ────────────────────────────────────────────────────────────
async def main():
    print("widok ui starting")
    await ui_loop()
asyncio.run(main())s
"""
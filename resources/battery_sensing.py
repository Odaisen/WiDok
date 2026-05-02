# Programmer: Odaisen
# Last Update: 01/05/26

# =========================
# IMPORTS / DEFINITIONS
# =========================

from machine import ADC, Pin

BAT_PIN = 10
ATTN = ADC.ATTN_6DB
VREF = 2.2
V_SCALING = 2
adc = ADC(Pin(BAT_PIN), atten=ATTN)

def read_battery_v(samples=64):
    total = 0
    for _ in range(samples):
        total += adc.read_u16()
    raw = total // samples
    vol_batt = (raw * VREF / 65535) * V_SCALING
    if vol_batt <= 3.3:
        pct_batt = 0
    elif vol_batt >= 4.2:
        pct_batt = 100
    else:
        pct_batt = int((vol_batt - 3.3) * 100 / (4.2 - 3.3))

    return vol_batt, pct_batt
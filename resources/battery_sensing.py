# Programmer: Odaisen
# Last Update: 02/05/26

from machine import ADC, Pin
BAT_PIN = 10
ATTN = ADC.ATTN_6DB
VREF = 2.2 # TODO: Calibrate after connecting battery
V_SCALING = 2
_adc = None

# ADC initialization check (prevents pin resets)
def _get_adc():
    global _adc
    if _adc is None:
        _adc = ADC(Pin(BAT_PIN), atten=ATTN)
    return _adc

# Returns (voltage, percent). Raises on hardware errors.
def read_battery_v(samples=64):
    adc = _get_adc()
    readings = 0
    for _ in range(max(1, int(samples))): # Extra safety for samples < 1
        readings += adc.read_u16()
    raw = readings // max(1, int(samples))
    vol_batt = (raw * VREF / 65535.0) * V_SCALING # Raw to volts
    if vol_batt <= 3.3: # Clamps max/min and maps percent
        pct_batt = 0
    elif vol_batt >= 4.2:
        pct_batt = 100
    else:
        pct_batt = int((vol_batt - 3.3) * 100 / (4.2 - 3.3))
    return vol_batt, pct_batt
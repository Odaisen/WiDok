# Programmer: Odaisen
# Last Update: 02/05/26

from machine import ADC, Pin
BAT_PIN = 10
ATTN = ADC.ATTN_6DB     # ~2.2 V full scale
VREF = 2.2              # Effective reference at 6 dB (~2.2 V on ESP32)
V_SCALING = 2           # Divider factor
_adc = None
def _get_adc():
    global _adc
    if _adc is None:
        _adc = ADC(Pin(BAT_PIN), atten=ATTN)
    return _adc
def read_battery_v(samples=64):
    """
    Returns (voltage, percent). Raises on hardware errors.
    """
    adc = _get_adc()
    total = 0
    for _ in range(max(1, int(samples))):
        total += adc.read_u16()
    raw = total // max(1, int(samples))
    # Convert raw to volts at battery node
    vol_batt = (raw * VREF / 65535.0) * V_SCALING
    # Clamp and map to percent
    if vol_batt <= 3.3:
        pct_batt = 0
    elif vol_batt >= 4.2:
        pct_batt = 100
    else:
        pct_batt = int((vol_batt - 3.3) * 100 / (4.2 - 3.3))
    return vol_batt, pct_batt
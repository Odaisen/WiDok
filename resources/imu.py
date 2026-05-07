# Programmer: Odaisen
# Last Update: 02/05/26

from machine import Pin, I2C
import resources.user_signaling as io
_latest_raw = (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
_latest_fused = (1.0, 0.0, 0.0, 0.0)
_i2c = None

# Initialize and cache I2C for the IMU. Returns the I2C handle (or None on failure)
def init(freq=100_000):
    global _i2c
    if _i2c:
        return _i2c
    try:
        sda = Pin(14, Pin.OPEN_DRAIN, pull=Pin.PULL_UP)
        scl = Pin(21, Pin.OPEN_DRAIN, pull=Pin.PULL_UP)
        _i2c = I2C(1, scl=scl, sda=sda, freq=freq)
    except Exception as e:
        io.signal(104, e)
        _i2c = None
    return _i2c

# Read sensor and update cached values
def update(): # TODO: Add code to actually read sensor data after IMU is fixed
    global _latest_raw, _latest_fused
    # RAW
    ax, ay, az = 0.0, 0.0, 1.0
    gx, gy, gz = 0.0, 0.0, 0.0
    _latest_raw = (ax, ay, az, gx, gy, gz)
    # FUSION
    qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
    _latest_fused = (qw, qx, qy, qz)

def read_raw():
    return _latest_raw

def get_fused():
    return _latest_fused

def reset():
    global _latest_fused
    _latest_fused = (1.0, 0.0, 0.0, 0.0)
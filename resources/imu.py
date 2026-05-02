# Programmer: Odaisen
# Last Update: 01/05/26

# =========================
# IMPORTS
# =========================

from machine import Pin, I2C
import struct
import time

# =========================
# INTERNAL STATE
# =========================

_latest_raw = (0,0,0,0,0,0)
_latest_fused = (1,0,0,0)

# =========================
# SENSOR INIT
# =========================

def init():
    sda = Pin(14, Pin.OPEN_DRAIN, Pin.PULL_UP)
    scl = Pin(21, Pin.OPEN_DRAIN, Pin.PULL_UP)
    i2c = I2C(1, scl=scl, sda=sda, freq=100_000)
    return i2c

# =========================
# UPDATE SENSOR
# =========================

def update():
    global _latest_raw, _latest_fused

    # ---- READ SENSOR HERE ----
    ax, ay, az = 0.0, 0.0, 1.0
    gx, gy, gz = 0.0, 0.0, 0.0

    _latest_raw = (ax, ay, az, gx, gy, gz)

    # ---- FUSION (placeholder quaternion) ----
    qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0
    _latest_fused = (qw, qx, qy, qz)

# =========================
# GETTERS (used by main)
# =========================

def read_raw():
    return _latest_raw

def get_fused():
    return _latest_fused

# =========================
# OPTIONAL HELPERS
# =========================

def reset():
    global _latest_fused
    _latest_fused = (1,0,0,0)
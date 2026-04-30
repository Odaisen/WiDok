# Programmer: Odaisen
# IMU module

import time

# =========================
# INTERNAL STATE
# =========================

_latest_raw = (0,0,0,0,0,0)
_latest_fused = (1,0,0,0)

# =========================
# SENSOR INIT (placeholder)
# =========================

def init():
    # init I2C, IMU chip, etc
    pass

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
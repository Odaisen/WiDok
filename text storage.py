charger_task = asyncio.create_task(
        ac_drive(freq_hz=275000, duration_ms=10000, dead_us=200)
    )


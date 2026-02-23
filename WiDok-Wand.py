# Imports
import asyncio
import "Resources.Bluetooth-Protocol"

# Bluetooth initialization

async def main():
    write_IMU = asyncio.create_task(_bluetooth_write(characteristic="_BLE_IMU_CHAR_ID"))
    await_connection = asyncio.create_task(_bluetooth_await_connection())
    await asyncio.gather(write_IMU, await_connection)

asyncio.run(main())
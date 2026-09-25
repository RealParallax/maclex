import asyncio
from bleak import BleakScanner

async def _scan():
    devices = await BleakScanner.discover(timeout=5.0)
    results = []
    for device in devices:
        results.append({
            "name": device.name,
            "address": device.address,
            "rssi": getattr(device, "rssi", None),
        })
    return results

def scan_bluetooth():
    return asyncio.run(_scan())

if __name__ == "__main__":
    for device in scan_bluetooth():
        print(
            f"{device['name'] or '(unnamed)':30} "
            f"{device['address']}  RSSI={device['rssi']}"
        )

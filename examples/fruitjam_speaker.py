# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time
import adafruit_fruitjam

pobj = adafruit_fruitjam.peripherals.Peripherals()
dac = pobj.dac  # use Fruit Jam's codec

# Route once for speaker
dac.headphone_output = False
dac.speaker_output = True

FILES = ["beep.wav", "dip.wav", "rise.wav"]
VOLUMES_DB = [12, 6, 0, -6, -12]

while True:
    print("\n=== Speaker Test ===")
    for vol in VOLUMES_DB:
        dac.dac_volume = vol
        print(f"Speaker volume: {vol} dB")
        for f in FILES:
            print(f"  -> {f}")
            pobj.play_file(f)
            time.sleep(0.2)
    time.sleep(1.0)

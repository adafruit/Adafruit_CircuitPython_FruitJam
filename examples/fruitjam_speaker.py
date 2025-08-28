# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import time

import adafruit_fruitjam

pobj = adafruit_fruitjam.peripherals.Peripherals(audio_output="speaker")

FILES = ["beep.wav", "dip.wav", "rise.wav"]
VOLUMES = [5, 7, 10, 11, 12]

while True:
    print("\n=== Speaker Test ===")
    for vol in VOLUMES:
        pobj.volume = vol
        print(f"Speaker volume: {vol}")
        for f in FILES:
            print(f"  -> {f}")
            pobj.play_file(f)
            time.sleep(0.2)
    time.sleep(1.0)

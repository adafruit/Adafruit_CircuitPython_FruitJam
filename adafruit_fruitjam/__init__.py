# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_fruitjam`
================================================================================

Helper library for the FruitJam board


* Author(s): Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit Fruit Jam <url>`_"

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"

from adafruit_fruitjam.peripherals import Peripherals


class FruitJam:
    def __init__(self):
        self.peripherals = Peripherals()


    @property
    def neopixels(self):
        return self.peripherals.neopixels

    @property
    def button1(self):
        return self.peripherals.button1

    @property
    def button2(self):
        return self.peripherals.button2

    @property
    def button3(self):
        return self.peripherals.button3

    @property
    def audio(self):
        return self.peripherals.audio

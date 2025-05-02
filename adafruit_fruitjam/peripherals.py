# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_fruitjam.peripherals`
================================================================================

Hardware peripherals for Adafruit Fruit Jam


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

import board
import displayio
import framebufferio
import picodvi
import supervisor

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"

VALID_DISPLAY_SIZES = {(360, 200), (720, 400), (320, 240), (640, 480)}
COLOR_DEPTH_LUT = {
    360: 16,
    320: 16,
    720: 8,
    640: 8,
}


def request_display_config(width, height):
    """
    Request a display size configuration. If the display is un-initialized,
    or is currently using a different configuration it will be initialized
    to the requested width and height.

    This function will set the initialized display to ``supervisor.runtime.display``

    :param width: The width of the display in pixels.
    :param height: The height of the display in pixels.
    :return: None
    """
    if (width, height) not in VALID_DISPLAY_SIZES:
        raise ValueError(f"Invalid display size. Must be one of: {VALID_DISPLAY_SIZES}")

    displayio.release_displays()
    fb = picodvi.Framebuffer(
        width,
        height,
        clk_dp=board.CKP,
        clk_dn=board.CKN,
        red_dp=board.D0P,
        red_dn=board.D0N,
        green_dp=board.D1P,
        green_dn=board.D1N,
        blue_dp=board.D2P,
        blue_dn=board.D2N,
        color_depth=COLOR_DEPTH_LUT[width],
    )
    supervisor.runtime.display = framebufferio.FramebufferDisplay(fb)

# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams, written for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Tim Cocks, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
`adafruit_fruitjam.graphics`
================================================================================

Graphics Helper library for the Adafruit Fruit Jam.

* Author(s): Melissa LeBlanc-Williams, Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit Fruit Jam <https://www.adafruit.com/product/6200>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

import supervisor
from adafruit_portalbase.graphics import GraphicsBase

from adafruit_fruitjam.peripherals import request_display_config

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"


class Graphics(GraphicsBase):
    """Graphics Helper library for the Adafruit Fruit Jam.

    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param int width: The total width of the display(s) in Pixels. Defaults to 64.
    :param int height: The total height of the display(s) in Pixels. Defaults to 32.
    :param int bit_depth: The number of bits per color channel. Defaults to 2.
    :param list alt_addr_pins: An alternate set of address pins to use. Defaults to None
    :param string color_order: A string containing the letter "R", "G", and "B" in the
                               order you want. Defaults to "RGB"
    :param bool Serpentine: Used when panels are arranged in a serpentine pattern rather
                            than a Z-pattern. Defaults to True.
    :param int tiles_rows: Used to indicate the number of rows the panels are arranged in.
                           Defaults to 1.
    :param debug: Turn on debug print outs. Defaults to False.

    """

    def __init__(
        self,
        **kwargs,
    ):
        default_bg = 0x000000
        debug = False
        if "default_bg" in kwargs:
            default_bg = kwargs.pop("default_bg")
        if "debug" in kwargs:
            debug = kwargs.pop("debug")

        if supervisor.runtime.display is None:
            request_display_config(640, 480)
        super().__init__(supervisor.runtime.display, default_bg=default_bg, debug=debug)

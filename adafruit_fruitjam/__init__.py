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

* `Adafruit Fruit Jam <https://www.adafruit.com/product/6200>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"

import gc
import os
import time

import board
import busio
import supervisor
import terminalio
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_portalbase import PortalBase
from digitalio import DigitalInOut

from adafruit_fruitjam.graphics import Graphics
from adafruit_fruitjam.network import CONTENT_IMAGE, CONTENT_JSON, CONTENT_TEXT, Network
from adafruit_fruitjam.peripherals import Peripherals


class FruitJam(PortalBase):
    """Class representing the Adafruit Fruit Jam.

    :param url: The URL of your data source. Defaults to ``None``.
    :param headers: The headers for authentication, typically used by Azure API's.
    :param json_path: The list of json traversal to get data out of. Can be list of lists for
                      multiple data points. Defaults to ``None`` to not use json.
    :param regexp_path: The list of regexp strings to get data out (use a single regexp group). Can
                        be list of regexps for multiple data points. Defaults to ``None`` to not
                        use regexp.
    :param convert_image: Determine whether or not to use the AdafruitIO image converter service.
                          Set as False if your image is already resized. Defaults to True.
    :param default_bg: The path to your default background image file or a hex color.
                       Defaults to 0x000000.
    :param status_neopixel: The pin for the status NeoPixel. Use ``board.NEOPIXEL`` for the on-board
                            NeoPixel. Defaults to ``None``, not the status LED
    :param str text_font: The path to your font file for your data text display.
    :param text_position: The position of your extracted text on the display in an (x, y) tuple.
                          Can be a list of tuples for when there's a list of json_paths, for example
    :param text_color: The color of the text, in 0xRRGGBB format. Can be a list of colors for when
                       there's multiple texts. Defaults to ``None``.
    :param text_wrap: Whether or not to wrap text (for long text data chunks). Defaults to
                      ``False``, no wrapping.
    :param text_maxlen: The max length of the text for text wrapping. Defaults to 0.
    :param text_transform: A function that will be called on the text before display
    :param int text_scale: The factor to scale the default size of the text by
    :param json_transform: A function or a list of functions to call with the parsed JSON.
                           Changes and additions are permitted for the ``dict`` object.
    :param image_json_path: The JSON traversal path for a background image to display. Defaults to
                            ``None``.
    :param image_resize: What size to resize the image we got from the json_path, make this a tuple
                         of the width and height you want. Defaults to ``None``.
    :param image_position: The position of the image on the display as an (x, y) tuple. Defaults to
                           ``None``.
    :param image_dim_json_path: The JSON traversal path for the original dimensions of image tuple.
                                Used with fetch(). Defaults to ``None``.
    :param success_callback: A function we'll call if you like, when we fetch data successfully.
                             Defaults to ``None``.
    :param str caption_text: The text of your caption, a fixed text not changed by the data we get.
                             Defaults to ``None``.
    :param str caption_font: The path to the font file for your caption. Defaults to ``None``.
    :param caption_position: The position of your caption on the display as an (x, y) tuple.
                             Defaults to ``None``.
    :param caption_color: The color of your caption. Must be a hex value, e.g. ``0x808000``.
    :param image_url_path: The HTTP traversal path for a background image to display.
                             Defaults to ``None``.
    :param esp: A passed ESP32 object, Can be used in cases where the ESP32 chip needs to be used
                             before calling the pyportal class. Defaults to ``None``.
    :param busio.SPI external_spi: A previously declared spi object. Defaults to ``None``.
    :param debug: Turn on debug print outs. Defaults to False.

    """

    def __init__(  # noqa: PLR0912,PLR0913,Too many branches,Too many arguments in function definition
        self,
        *,
        url=None,
        headers=None,
        json_path=None,
        regexp_path=None,
        convert_image=True,
        default_bg=0x000000,
        status_neopixel=None,
        text_font=terminalio.FONT,
        text_position=None,
        text_color=0x808080,
        text_wrap=False,
        text_maxlen=0,
        text_transform=None,
        text_scale=1,
        json_transform=None,
        image_json_path=None,
        image_resize=None,
        image_position=None,
        image_dim_json_path=None,
        caption_text=None,
        caption_font=None,
        caption_position=None,
        caption_color=0x808080,
        image_url_path=None,
        success_callback=None,
        esp=None,
        external_spi=None,
        debug=False,
        secrets_data=None,
    ):
        graphics = Graphics(
            default_bg=default_bg,
            debug=debug,
        )
        self._default_bg = default_bg

        spi = board.SPI()

        if image_json_path or image_url_path:
            if debug:
                print("Init image path")
            if not image_position:
                image_position = (0, 0)  # default to top corner
            if not image_resize:
                image_resize = (
                    self.display.width,
                    self.display.height,
                )  # default to full screen

        if esp is None:
            esp32_cs = DigitalInOut(board.ESP_CS)
            esp32_ready = DigitalInOut(board.ESP_BUSY)
            esp32_reset = DigitalInOut(board.ESP_RESET)
            spi = board.SPI()
            esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

        self.peripherals = Peripherals()

        network = Network(
            status_neopixel=self.peripherals.neopixels
            if status_neopixel is None or status_neopixel == board.NEOPIXEL
            else status_neopixel,
            esp=esp,
            external_spi=spi,
            extract_values=False,
            convert_image=convert_image,
            image_url_path=image_url_path,
            image_json_path=image_json_path,
            image_resize=image_resize,
            image_position=image_position,
            image_dim_json_path=image_dim_json_path,
            debug=debug,
        )
        self.url = url

        super().__init__(
            network,
            graphics,
            url=url,
            headers=headers,
            json_path=json_path,
            regexp_path=regexp_path,
            json_transform=json_transform,
            success_callback=success_callback,
            debug=debug,
        )

        # Convenience Shortcuts for compatibility

        self.sd_check = self.peripherals.sd_check
        self.play_file = self.peripherals.play_file
        self.stop_play = self.peripherals.stop_play
        self.volume = self.peripherals.volume
        self.audio_output = self.peripherals.audio_output

        self.image_converter_url = self.network.image_converter_url
        self.wget = self.network.wget
        self.show_QR = self.graphics.qrcode
        self.hide_QR = self.graphics.hide_QR

        if default_bg is not None:
            self.graphics.set_background(default_bg)

        if self._debug:
            print("Init caption")
        if caption_font:
            self._caption_font = self._load_font(caption_font)
        if caption_text is not None:
            self.set_caption(caption_text, caption_position, caption_color)

        if text_font:
            if text_position is not None and isinstance(text_position[0], (list, tuple)):
                num = len(text_position)
                if not text_wrap:
                    text_wrap = [0] * num
                if not text_maxlen:
                    text_maxlen = [0] * num
                if not text_transform:
                    text_transform = [None] * num
                if not isinstance(text_scale, (list, tuple)):
                    text_scale = [text_scale] * num
            else:
                num = 1
                text_position = (text_position,)
                text_color = (text_color,)
                text_wrap = (text_wrap,)
                text_maxlen = (text_maxlen,)
                text_transform = (text_transform,)
                text_scale = (text_scale,)
            for i in range(num):
                self.add_text(
                    text_position=text_position[i],
                    text_font=text_font,
                    text_color=text_color[i],
                    text_wrap=text_wrap[i],
                    text_maxlen=text_maxlen[i],
                    text_transform=text_transform[i],
                    text_scale=text_scale[i],
                )
        else:
            self._text_font = None
            self._text = None

        gc.collect()

    def sync_time(self, **kwargs):
        """Set the system RTC via NTP using this FruitJam's Network.

        This is a convenience wrapper for ``self.network.sync_time(...)``.

        :param str server: Override NTP host (defaults to ``NTP_SERVER`` or
            ``"pool.ntp.org"`` if unset).  (Pass via ``server=...`` in kwargs.)
        :param float tz_offset: Override hours from UTC (defaults to ``NTP_TZ``;
            ``NTP_DST`` is still added).  (Pass via ``tz_offset=...``.)
        :param dict tuning: Advanced options dict (optional). Supported keys:
            ``timeout`` (float, socket timeout seconds; defaults to ``NTP_TIMEOUT`` or 5.0),
            ``cache_seconds`` (int; defaults to ``NTP_CACHE_SECONDS`` or 0),
            ``require_year`` (int; defaults to ``NTP_REQUIRE_YEAR`` or 2022).
            (Pass via ``tuning={...}``.)

        :returns: Synced time
        :rtype: time.struct_time
        """
        return self.network.sync_time(**kwargs)

    def set_caption(self, caption_text, caption_position, caption_color):
        """A caption. Requires setting ``caption_font`` in init!

        :param caption_text: The text of the caption.
        :param caption_position: The position of the caption text.
        :param caption_color: The color of your caption text. Must be a hex value, e.g.
                              ``0x808000``.
        """
        if self._debug:
            print("Setting caption to", caption_text)

        if (not caption_text) or (not self._caption_font) or (not caption_position):
            return  # nothing to do!

        index = self.add_text(
            text_position=caption_position,
            text_font=self._caption_font,
            text_color=caption_color,
            is_data=False,
        )
        self.set_text(caption_text, index)

    def fetch(self, refresh_url=None, timeout=10, force_content_type=None):  # noqa: PLR0912 Too many branches
        """Fetch data from the url we initialized with, perfom any parsing,
        and display text or graphics. This function does pretty much everything
        Optionally update the URL
        """

        if refresh_url:
            self.url = refresh_url

        response = self.network.fetch(self.url, headers=self._headers, timeout=timeout)

        json_out = None
        if not force_content_type:
            content_type = self.network.check_response(response)
        else:
            content_type = force_content_type
        json_path = self._json_path

        if content_type == CONTENT_JSON:
            if json_path is not None:
                # Drill down to the json path and set json_out as that node
                if isinstance(json_path, (list, tuple)) and (
                    not json_path or not isinstance(json_path[0], (list, tuple))
                ):
                    json_path = (json_path,)
            try:
                gc.collect()
                json_out = response.json()
                if self._debug:
                    print(json_out)
                gc.collect()
            except ValueError:  # failed to parse?
                print("Couldn't parse json: ", response.text)
                raise
            except MemoryError:
                supervisor.reload()
        if content_type == CONTENT_IMAGE:
            try:
                filename, position = self.network.process_image(
                    json_out, self.peripherals.sd_check()
                )
                if filename and position is not None:
                    self.graphics.set_background(filename, position)
            except ValueError as error:
                print("Error displaying cached image. " + error.args[0])
                if self._default_bg is not None:
                    self.graphics.set_background(self._default_bg)
            except KeyError as error:
                print("Error finding image data. '" + error.args[0] + "' not found.")
                self.set_background(self._default_bg)

        if content_type == CONTENT_JSON:
            values = self.network.process_json(json_out, json_path)
        elif content_type == CONTENT_TEXT:
            values = self.network.process_text(response.text, self._regexp_path)

        # if we have a callback registered, call it now
        if self._success_callback:
            self._success_callback(values)

        self._fill_text_labels(values)
        # Clean up
        json_out = None
        response = None
        gc.collect()

        if len(values) == 1:
            values = values[0]

        return values

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

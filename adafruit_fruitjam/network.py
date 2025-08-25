# SPDX-FileCopyrightText: 2020 Melissa LeBlanc-Williams, written for Adafruit Industries
# SPDX-FileCopyrightText: 2025 Tim Cocks, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""
`adafruit_fruitjam.network`
================================================================================

CircuitPython PortalBase network driver for Adafruit Fruit Jam.

* Author(s): Limor Fried, Kevin J. Walters, Melissa LeBlanc-Williams, Tim Cocks

Implementation Notes
--------------------

**Hardware:**

* `Adafruit Fruit Jam <https://www.adafruit.com/product/6200>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases

"""

import gc
import os
import time

import adafruit_connection_manager as acm
import adafruit_ntp
import microcontroller
import neopixel
import rtc
from adafruit_portalbase.network import (
    CONTENT_IMAGE,
    CONTENT_JSON,
    CONTENT_TEXT,
    NetworkBase,
)
from adafruit_portalbase.wifi_coprocessor import WiFi

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"

# you'll need to pass in an io username, width, height, format (bit depth), io key, and then url!
IMAGE_CONVERTER_SERVICE = (
    "https://io.adafruit.com/api/v2/%s/integrations/image-formatter?"
    "x-aio-key=%s&width=%d&height=%d&output=BMP%d&url=%s"
)


class Network(NetworkBase):
    """CircuitPython PortalBase network driver for Adafruit Fruit Jam.

    :param status_neopixel: The pin for the status NeoPixel. Use ``board.NEOPIXEL`` for the on-board
                            NeoPixel. Defaults to ``None``, not the status LED. Or pass an
                            instantiated NeoPixel object.
    :param esp: A passed ESP32 object, Can be used in cases where the ESP32 chip needs to be used
                             before calling the fruitjam class. Defaults to ``None``.
    :param busio.SPI external_spi: A previously declared spi object. Defaults to ``None``.
    :param bool extract_values: If true, single-length fetched values are automatically extracted
                                from lists and tuples. Defaults to ``True``.
    :param debug: Turn on debug print outs. Defaults to False.
    :param convert_image: Determine whether or not to use the AdafruitIO image converter service.
                          Set as False if your image is already resized. Defaults to True.
    :param image_url_path: The HTTP traversal path for a background image to display.
                             Defaults to ``None``.
    :param image_json_path: The JSON traversal path for a background image to display. Defaults to
                            ``None``.
    :param image_resize: What size to resize the image we got from the json_path, make this a tuple
                         of the width and height you want. Defaults to ``None``.
    :param image_position: The position of the image on the display as an (x, y) tuple. Defaults to
                           ``None``.
    :param image_dim_json_path: The JSON traversal path for the original dimensions of image tuple.
                                Used with fetch(). Defaults to ``None``.

    """

    def __init__(  # noqa: PLR0913 Too many arguments in function definition
        self,
        *,
        status_neopixel=None,
        esp=None,
        external_spi=None,
        extract_values=True,
        debug=False,
        convert_image=True,
        image_url_path=None,
        image_json_path=None,
        image_resize=None,
        image_position=None,
        image_dim_json_path=None,
    ):
        if isinstance(status_neopixel, microcontroller.Pin):
            status_led = neopixel.NeoPixel(status_neopixel, 1, brightness=0.2)
        elif isinstance(status_neopixel, neopixel.NeoPixel):
            status_led = status_neopixel
        else:
            status_led = None

        wifi = WiFi(status_led=status_led, esp=esp, external_spi=external_spi)

        super().__init__(
            wifi,
            extract_values=extract_values,
            debug=debug,
        )

        self._convert_image = convert_image
        self._image_json_path = image_json_path
        self._image_url_path = image_url_path
        self._image_resize = image_resize
        self._image_position = image_position
        self._image_dim_json_path = image_dim_json_path
        gc.collect()

    @property
    def ip_address(self):
        """Return the IP Address nicely formatted"""
        return self._wifi.esp.pretty_ip(self._wifi.esp.ip_address)

    def image_converter_url(self, image_url, width, height, color_depth=16):
        """Generate a converted image url from the url passed in,
        with the given width and height. aio_username and aio_key must be
        set in secrets."""
        try:
            aio_username = self._get_setting("AIO_USERNAME")
            aio_key = self._get_setting("AIO_KEY")
        except KeyError as error:
            raise KeyError(
                "\n\nOur image converter service require a login/password to rate-limit. "
                "Please register for a free adafruit.io account and place the user/key in "
                "your secrets file under 'aio_username' and 'aio_key'"
            ) from error

        return IMAGE_CONVERTER_SERVICE % (
            aio_username,
            aio_key,
            width,
            height,
            color_depth,
            image_url,
        )

    def process_image(self, json_data, sd_card=False):  # noqa: PLR0912 Too many branches
        """
        Process image content

        :param json_data: The JSON data that we can pluck values from
        :param bool sd_card: Whether or not we have an SD card inserted

        """
        filename = None
        position = None
        image_url = None

        if self._image_url_path:
            image_url = self._image_url_path

        if self._image_json_path:
            image_url = self.json_traverse(json_data, self._image_json_path)

        iwidth = 0
        iheight = 0
        if self._image_dim_json_path:
            iwidth = int(self.json_traverse(json_data, self._image_dim_json_path[0]))
            iheight = int(self.json_traverse(json_data, self._image_dim_json_path[1]))
            print("image dim:", iwidth, iheight)

        if image_url:
            print("original URL:", image_url)
            if self._convert_image:
                if iwidth < iheight:
                    image_url = self.image_converter_url(
                        image_url,
                        int(self._image_resize[1] * self._image_resize[1] / self._image_resize[0]),
                        self._image_resize[1],
                    )
                else:
                    image_url = self.image_converter_url(
                        image_url, self._image_resize[0], self._image_resize[1]
                    )

                print("convert URL:", image_url)
            # convert image to bitmap and cache
            # print("**not actually wgetting**")
            filename = "/cache.bmp"
            chunk_size = 4096  # default chunk size is 12K (for QSPI)
            if sd_card:
                filename = "/sd" + filename
                chunk_size = 512  # current bug in big SD writes -> stick to 1 block
            try:
                self.wget(image_url, filename, chunk_size=chunk_size)
            except OSError as error:
                raise OSError(
                    """\n\nNo writable filesystem found for saving datastream.
                    Insert an SD card or set internal filesystem to be unsafe by
                    setting 'disable_concurrent_write_protection' in the mount options in boot.py"""
                ) from error
            except RuntimeError as error:
                raise RuntimeError("wget didn't write a complete file") from error
            if iwidth < iheight:
                pwidth = int(self._image_resize[1] * self._image_resize[1] / self._image_resize[0])
                position = (
                    self._image_position[0] + int((self._image_resize[0] - pwidth) / 2),
                    self._image_position[1],
                )
            else:
                position = self._image_position

            image_url = None
            gc.collect()

        return filename, position

    def sync_time(self, server=None, tz_offset=None, tuning=None):
        """
        Set the system RTC via NTP using this Network's Wi-Fi connection.

        Reads optional settings from settings.toml:

          NTP_SERVER        – NTP host (default: "pool.ntp.org")
          NTP_TZ            – timezone offset in hours (float, default: 0)
          NTP_DST           – extra offset for daylight saving (0=no, 1=yes; default: 0)
          NTP_INTERVAL      – re-sync interval in seconds (default: 3600, not used internally,
                               but available for user loop scheduling)

          NTP_TIMEOUT       – socket timeout per attempt (seconds, default: 5.0)
          NTP_CACHE_SECONDS – cache results, 0 = always fetch fresh (default: 0)
          NTP_REQUIRE_YEAR  – minimum acceptable year (default: 2022)

          NTP_RETRIES       – number of NTP fetch attempts on timeout (default: 8)
          NTP_DELAY_S       – delay between retries in seconds (default: 1.0)

        Keyword args:
          server (str)        – override NTP_SERVER
          tz_offset (float)   – override NTP_TZ (+ NTP_DST still applied)
          tuning (dict)       – override tuning knobs, e.g.:
                                {
                                    "timeout": 5.0,
                                    "cache_seconds": 0,
                                    "require_year": 2022,
                                    "retries": 8,
                                    "retry_delay": 1.0,
                                }

        Returns:
          time.struct_time
        """
        # Bring up Wi-Fi using the existing flow.
        self.connect()

        # Build a socket pool from the existing ESP interface.
        pool = acm.get_radio_socketpool(self._wifi.esp)

        # Settings with environment fallbacks.
        server = server or os.getenv("NTP_SERVER") or "pool.ntp.org"

        if tz_offset is None:
            tz_env = os.getenv("NTP_TZ")
            try:
                tz_offset = float(tz_env) if tz_env not in {None, ""} else 0.0
            except Exception:
                tz_offset = 0.0

        # Simple DST additive offset (no IANA time zone logic).
        try:
            dst = float(os.getenv("NTP_DST") or 0)
        except Exception:
            dst = 0.0
        tz_offset += dst

        # Optional tuning (env can override passed defaults).
        t = tuning or {}

        def _f(name, default):
            v = os.getenv(name)
            try:
                return float(v) if v not in {None, ""} else float(default)
            except Exception:
                return float(default)

        def _i(name, default):
            v = os.getenv(name)
            try:
                return int(v) if v not in {None, ""} else int(default)
            except Exception:
                return int(default)

        timeout = float(t.get("timeout", _f("NTP_TIMEOUT", 5.0)))
        cache_seconds = int(t.get("cache_seconds", _i("NTP_CACHE_SECONDS", 0)))
        require_year = int(t.get("require_year", _i("NTP_REQUIRE_YEAR", 2022)))

        # Query NTP and set the system RTC.
        ntp = adafruit_ntp.NTP(
            pool,
            server=server,
            tz_offset=tz_offset,
            socket_timeout=timeout,
            cache_seconds=cache_seconds,
        )

        # Multiple reply attempts on transient timeouts
        ntp_retries = int(t.get("retries", _i("NTP_RETRIES", 8)))
        ntp_delay_s = float(t.get("retry_delay", _f("NTP_DELAY_S", 1.0)))

        last_exc = None
        for attempt in range(ntp_retries):
            try:
                now = ntp.datetime  # struct_time
                break  # success
            except OSError as e:
                last_exc = e
                # Only retry on timeout-like errors
                if getattr(e, "errno", None) == 116 or "ETIMEDOUT" in str(e):
                    # Reassert Wi-Fi via existing policy, then wait a bit
                    self.connect()
                    if self._debug:
                        print("NTP timeout, retry", attempt + 1, "of", ntp_retries)
                    time.sleep(ntp_delay_s)
                    continue
                # Non-timeout: don't spin
                break

        if last_exc and "now" not in locals():
            raise last_exc

        if now.tm_year < require_year:
            raise RuntimeError("NTP returned an unexpected year; not setting RTC")

        rtc.RTC().datetime = now
        return now

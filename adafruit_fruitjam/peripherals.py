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

* `Adafruit Fruit Jam <https://www.adafruit.com/product/6200>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

# * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""

import os

import adafruit_sdcard
import adafruit_tlv320
import audiobusio
import audiocore
import board
import busio
import digitalio
import displayio
import framebufferio
import picodvi
import simpleio
import storage
import supervisor
from digitalio import DigitalInOut, Direction, Pull
from neopixel import NeoPixel

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_FruitJam.git"

VALID_DISPLAY_SIZES = {(360, 200), (720, 400), (320, 240), (640, 480)}
COLOR_DEPTH_LUT = {
    360: 16,
    320: 16,
    720: 8,
    640: 8,
}


def request_display_config(width=None, height=None, color_depth=None):
    """
    Request a display size configuration. If the display is un-initialized,
    or is currently using a different configuration it will be initialized
    to the requested width and height.

    This function will set the initialized display to ``supervisor.runtime.display``

    :param width: The width of the display in pixels. Leave unspecified to default
      to the ``CIRCUITPY_DISPLAY_WIDTH`` environmental variable if provided. Otherwise,
      a ``ValueError`` exception will be thrown.
    :param height: The height of the display in pixels. Leave unspecified to default
      to the appropriate height for the provided width.
    :param color_depth: The color depth of the display in bits.
      Valid values are 1, 2, 4, 8, 16, 32. Larger resolutions must use
      smaller color_depths due to RAM limitations. Default color_depth for
      720 and 640 width is 8, and default color_depth for 320 and 360 width
      is 16.
    :return: None
    """
    # if user does not specify width, use default configuration
    if width is None and (width := os.getenv("CIRCUITPY_DISPLAY_WIDTH")) is None:
        raise ValueError("No CIRCUITPY_DISPLAY_WIDTH specified in settings.toml.")

    # check that we have a valid display size
    if (height is not None and (width, height) not in VALID_DISPLAY_SIZES) or (
        height is None and width not in [size[0] for size in VALID_DISPLAY_SIZES]
    ):
        raise ValueError(f"Invalid display size. Must be one of: {VALID_DISPLAY_SIZES}")

    # if user does not specify height, use matching height
    if height is None:
        height = next((h for w, h in VALID_DISPLAY_SIZES if width == w))

    # if user does not specify a requested color_depth
    if color_depth is None:
        # use the maximum color depth for given width
        color_depth = COLOR_DEPTH_LUT[width]

    requested_config = (width, height, color_depth)

    if requested_config != get_display_config():
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
            color_depth=color_depth,
        )
        supervisor.runtime.display = framebufferio.FramebufferDisplay(fb)


def get_display_config():
    """
    Get the current display size configuration.

    :return: display_config: Tuple containing the width, height, and color_depth of the display
      in pixels and bits respectively.
    """

    display = supervisor.runtime.display
    if display is not None:
        display_config = (display.width, display.height, display.framebuffer.color_depth)
        return display_config
    else:
        return (None, None, None)


class Peripherals:
    """Peripherals Helper Class for the FruitJam Library

    :param audio_output: The audio output interface to use 'speaker' or 'headphone'
    :param safe_volume_limit: The maximum volume allowed for the audio output. Default is 15
        Using higher values can damage some speakers, change at your own risk.

    Attributes:
        neopixels (NeoPxiels): The NeoPixels on the Fruit Jam board.
            See https://circuitpython.readthedocs.io/projects/neopixel/en/latest/api.html
    """

    def __init__(self, audio_output="headphone", safe_volume_limit=12):
        self.neopixels = NeoPixel(board.NEOPIXEL, 5)

        self._buttons = []
        for pin in (board.BUTTON1, board.BUTTON2, board.BUTTON3):
            switch = DigitalInOut(pin)
            switch.direction = Direction.INPUT
            switch.pull = Pull.UP
            self._buttons.append(switch)

        i2c = board.I2C()
        self._dac = adafruit_tlv320.TLV320DAC3100(i2c)

        # set sample rate & bit depth
        self._dac.configure_clocks(sample_rate=11030, bit_depth=16)

        self._audio_output = audio_output
        self.audio_output = audio_output
        self._audio = audiobusio.I2SOut(board.I2S_BCLK, board.I2S_WS, board.I2S_DIN)
        if safe_volume_limit < 1 or safe_volume_limit > 20:
            raise ValueError("safe_volume_limit must be between 1 and 20")
        self.safe_volume_limit = safe_volume_limit
        self._volume = 7
        self._apply_volume()

        self._sd_mounted = False
        sd_pins_in_use = False
        SD_CS = board.SD_CS
        # try to Connect to the sdcard card and mount the filesystem.
        try:
            # initialze CS pin
            cs = digitalio.DigitalInOut(SD_CS)
        except ValueError:
            # likely the SDCard was auto-initialized by the core
            sd_pins_in_use = True

            # if placeholder.txt file does not exist
            if "placeholder.txt" not in os.listdir("/sd/"):
                self._sd_mounted = True

        if not sd_pins_in_use:
            try:
                # if sd CS pin was not in use
                # try to initialize and mount the SDCard
                sdcard = adafruit_sdcard.SDCard(
                    busio.SPI(board.SD_SCK, board.SD_MOSI, board.SD_MISO), cs
                )
                vfs = storage.VfsFat(sdcard)
                storage.mount(vfs, "/sd")
                self._sd_mounted = True
            except OSError:
                # sdcard init or mounting failed
                self._sd_mounted = False

    @property
    def button1(self) -> bool:
        """
        Return whether Button 1 is pressed
        """
        return not self._buttons[0].value

    @property
    def button2(self) -> bool:
        """
        Return whether Button 2 is pressed
        """
        return not self._buttons[1].value

    @property
    def button3(self) -> bool:
        """
        Return whether Button 3 is pressed
        """
        return not self._buttons[2].value

    @property
    def any_button_pressed(self) -> bool:
        """
        Return whether any button is pressed
        """
        return True in [not button.value for (i, button) in enumerate(self._buttons)]

    @property
    def dac(self):
        return self._dac

    @property
    def audio(self):
        return self._audio

    def sd_check(self):
        return self._sd_mounted

    def play_file(self, file_name, wait_to_finish=True):
        """Play a wav file.

        :param str file_name: The name of the wav file to play on the speaker.
        :param bool wait_to_finish: flag to determine if this is a blocking call

        """

        # can't use `with` because we need wavefile to remain open after return
        self.wavfile = open(file_name, "rb")
        wavedata = audiocore.WaveFile(self.wavfile)
        self.audio.play(wavedata)
        if not wait_to_finish:
            return
        while self.audio.playing:
            pass
        self.wavfile.close()

    def stop_play(self):
        """Stops playing a wav file."""
        self.audio.stop()
        if self.wavfile is not None:
            self.wavfile.close()

    @property
    def volume(self) -> int:
        """
        The volume level of the Fruit Jam audio output. Valid values are 1-20.
        """
        return self._volume

    @volume.setter
    def volume(self, volume_level: int) -> None:
        """
        :param volume_level: new volume level 1-20
        :return: None
        """
        if not (1 <= volume_level <= 20):
            raise ValueError("Volume level must be between 1 and 20")

        if volume_level > self.safe_volume_limit:
            raise ValueError(
                f"Volume level must be less than or equal to "
                + f"safe_volume_limit: {self.safe_volume_limit}. "
                + f"Using higher values could damage speakers. "
                + f"To override this limitation pass a value larger {self.safe_volume_limit} "
                + f"for the safe_volume_limit argument of the constructor."
            )

        self._volume = volume_level
        self._apply_volume()

    @property
    def audio_output(self) -> str:
        """
        The audio output interface. 'speaker' or 'headphone'
        :return:
        """
        return self._audio_output

    @audio_output.setter
    def audio_output(self, audio_output: str) -> None:
        """

        :param audio_output: The audio interface to use 'speaker' or 'headphone'.
        :return: None
        """
        if audio_output == "headphone":
            self._dac.headphone_output = True
            self._dac.speaker_output = False
        elif audio_output == "speaker":
            self._dac.headphone_output = False
            self._dac.speaker_output = True
        else:
            raise ValueError("audio_output must be either 'headphone' or 'speaker'")

    def _apply_volume(self) -> None:
        """
        Map the basic volume level to a db value and set it on the DAC.
        """
        db_val = simpleio.map_range(self._volume, 1, 20, -63, 23)
        self._dac.dac_volume = db_val

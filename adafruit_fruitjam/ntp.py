# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
Fruit Jam NTP helper (one-shot)
- Reads Wi-Fi creds (CIRCUITPY_WIFI_SSID/PASSWORD)
- Reads optional NTP_* settings (server, tz, dst, interval, timeout, etc.)
- Connects AirLift, queries NTP, sets rtc.RTC().datetime
- Returns (now, next_sync) where next_sync is None if NTP_INTERVAL is 0/absent
"""

import os
import time

import adafruit_connection_manager as acm
import adafruit_ntp
import board
import rtc
from adafruit_esp32spi import adafruit_esp32spi
from digitalio import DigitalInOut


class _State:
    """Mutable holder to avoid module-level 'global' updates (ruff PLW0603)."""

    def __init__(self):
        self.spi = None
        self.cs = None
        self.rdy = None
        self.rst = None
        self.esp = None
        self.pool = None


_state = _State()


def _ensure_radio():
    if _state.esp and _state.pool:
        return _state.esp, _state.pool

    if _state.spi is None:
        _state.spi = board.SPI()

    if _state.cs is None:
        _state.cs = DigitalInOut(board.ESP_CS)
    if _state.rdy is None:
        _state.rdy = DigitalInOut(board.ESP_BUSY)
    if _state.rst is None:
        _state.rst = DigitalInOut(board.ESP_RESET)

    if _state.esp is None:
        _state.esp = adafruit_esp32spi.ESP_SPIcontrol(_state.spi, _state.cs, _state.rdy, _state.rst)

    if _state.pool is None:
        _state.pool = acm.get_radio_socketpool(_state.esp)

    return _state.esp, _state.pool


def _env_float(name, default):
    try:
        v = os.getenv(name)
        return float(v) if v not in {None, ""} else float(default)
    except Exception:
        return float(default)


def _env_int(name, default):
    try:
        v = os.getenv(name)
        return int(v) if v not in {None, ""} else int(default)
    except Exception:
        return int(default)


def sync_time(*, server=None, tz_offset=None, tuning=None):
    """
    One-call NTP sync. Small public API to satisfy ruff PLR0913.
      server: override NTP_SERVER
      tz_offset: override NTP_TZ (+ NTP_DST is still applied)
      tuning: optional dict to override timeouts/retries/cache/year check, e.g.:
              {"timeout": 5.0, "retries": 2, "retry_delay": 1.0,
               "cache_seconds": 0, "require_year": 2022}

    Returns (now, next_sync). next_sync is None if NTP_INTERVAL is disabled.
    """
    # Wi-Fi creds (required)
    ssid = os.getenv("CIRCUITPY_WIFI_SSID")
    pw = os.getenv("CIRCUITPY_WIFI_PASSWORD")
    if not ssid or not pw:
        raise RuntimeError("Add CIRCUITPY_WIFI_SSID/PASSWORD to settings.toml")

    # NTP config (env defaults, overridable by parameters)
    server = server or os.getenv("NTP_SERVER") or "pool.ntp.org"
    if tz_offset is None:
        tz_offset = _env_float("NTP_TZ", 0.0)
    tz_offset += _env_float("NTP_DST", 0.0)

    # Tuning knobs
    t = tuning or {}
    timeout = float(t.get("timeout", _env_float("NTP_TIMEOUT", 5.0)))
    retries = int(t.get("retries", _env_int("NTP_RETRIES", 2)))
    retry_delay = float(t.get("retry_delay", _env_float("NTP_DELAY_S", 1.0)))
    cache_seconds = int(t.get("cache_seconds", _env_int("NTP_CACHE_SECONDS", 0)))
    require_year = int(t.get("require_year", 2022))
    interval = _env_int("NTP_INTERVAL", 0)

    esp, pool = _ensure_radio()

    # Connect with light retries
    for attempt in range(retries + 1):
        try:
            if not esp.is_connected:
                esp.connect_AP(ssid, pw)
            break
        except Exception:
            if attempt >= retries:
                raise
            try:
                esp.reset()
            except Exception:
                pass
            time.sleep(retry_delay)

    ntp = adafruit_ntp.NTP(
        pool,
        tz_offset=tz_offset,
        server=server,
        socket_timeout=timeout,
        cache_seconds=cache_seconds,
    )

    now = ntp.datetime
    if now.tm_year < require_year:
        raise RuntimeError("NTP returned an unexpected year; not setting RTC")

    rtc.RTC().datetime = now
    next_sync = time.time() + interval if interval > 0 else None
    return now, next_sync


def release_pins():
    """Free pins if hot-reloading during development."""
    try:
        for pin in (_state.cs, _state.rdy, _state.rst):
            if pin:
                pin.deinit()
    finally:
        _state.spi = _state.cs = _state.rdy = _state.rst = _state.esp = _state.pool = None


def setup_ntp():
    """Retry wrapper that prints status; useful while developing."""
    print("Fetching time via NTP.")
    while True:
        try:
            now, next_sync = sync_time()
            break
        except Exception as ex:
            print("Exception:", ex)
            time.sleep(1)
    print("NTP OK, localtime:", time.localtime())
    return now, next_sync

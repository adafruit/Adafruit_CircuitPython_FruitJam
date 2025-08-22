# SPDX-FileCopyrightText: Copyright (c) 2025 Tim Cocks for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# see examples/settings.toml for NTP_ options
#
from adafruit_fruitjam.ntp import sync_time

now, next_sync = sync_time()
print("RTC set:", now)

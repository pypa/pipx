#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pipx.util import WINDOWS

if WINDOWS:
    stars = ""
    hazard = ""
    sleep = ""
else:
    stars = "✨ 🌟 ✨"
    hazard = "⚠️"
    sleep = "😴"

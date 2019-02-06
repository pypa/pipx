#!/usr/bin/env python
# -*- coding: utf-8 -*-

try:
    WindowsError
except NameError:
    WINDOWS = False
    stars = "✨ 🌟 ✨"
    hazard = "⚠️"
    sleep = "😴"
else:
    WINDOWS = True
    stars = ""
    hazard = ""
    sleep = ""

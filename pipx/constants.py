#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

DEFAULT_PYTHON = sys.executable
DEFAULT_PIPX_HOME = Path.home() / ".local/pipx"
DEFAULT_PIPX_BIN_DIR = Path.home() / ".local/bin"
PIPX_HOME = Path(os.environ.get("PIPX_HOME", DEFAULT_PIPX_HOME)).resolve()
PIPX_LOCAL_VENVS = PIPX_HOME / "venvs"
LOCAL_BIN_DIR = Path(os.environ.get("PIPX_BIN_DIR", DEFAULT_PIPX_BIN_DIR)).resolve()
PIPX_VENV_CACHEDIR = PIPX_HOME / ".cache"
PIPX_PACKAGE_NAME = "pipx"
TEMP_VENV_EXPIRATION_THRESHOLD_DAYS = 14

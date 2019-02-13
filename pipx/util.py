#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import logging
import shutil


class PipxError(Exception):
    pass


try:
    WindowsError
except NameError:
    WINDOWS = False
else:
    WINDOWS = True


def rmdir(path: Path):
    logging.info(f"removing directory {path}")
    if WINDOWS:
        os.system(f'rmdir /S /Q "{str(path)}"')
    else:
        shutil.rmtree(path)


def mkdir(path: Path) -> None:
    if path.is_dir():
        return
    logging.info(f"creating directory {path}")
    path.mkdir(parents=True, exist_ok=True)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pkg_resources
import sys

package = sys.argv[1]

for r in pkg_resources.get_distribution(package).requires():
    print(r)

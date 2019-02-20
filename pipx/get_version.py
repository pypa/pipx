#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

package = sys.argv[1]

try:
    import pkg_resources

    print(pkg_resources.get_distribution(package).version)
except Exception:
    pass

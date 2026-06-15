#!/usr/bin/env python3
"""blip 入口：python3 blip.py [-c config.toml]"""
import sys

from blipmon.app import main

if __name__ == "__main__":
    sys.exit(main())

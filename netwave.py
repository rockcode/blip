#!/usr/bin/env python3
"""netwave 入口：python3 netwave.py [-c config.toml]"""
import sys

from app import main

if __name__ == "__main__":
    sys.exit(main())

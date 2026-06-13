"""ANSI escape sequence helpers (truecolor). Pure string functions."""

ESC = "\x1b"

RESET = f"{ESC}[0m"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
CLEAR_SCREEN = f"{ESC}[2J"
CLEAR_BELOW = f"{ESC}[0J"
CLEAR_LINE = f"{ESC}[K"
HOME = f"{ESC}[H"

# 调色板 (r, g, b)
GREEN = (80, 220, 120)
YELLOW = (230, 200, 60)
RED = (235, 80, 80)
GRAY = (150, 150, 150)
DIM = (90, 90, 90)


def fg(rgb):
    r, g, b = rgb
    return f"{ESC}[38;2;{r};{g};{b}m"


def colorize(text, rgb):
    return f"{fg(rgb)}{text}{RESET}"


def move(row, col):
    """1-based 光标定位。"""
    return f"{ESC}[{row};{col}H"

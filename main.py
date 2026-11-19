#!/usr/bin/env python3
"""news-image-20261119: draws a one-day world-news front page as a 1024x1024 PNG.

Pure Python 3 standard library only (os, struct, zlib). No network, no files
read at runtime, no randomness, no clock. Fully deterministic: the same bytes
come out of every run.
"""

import math
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (250, 246, 236)
WHITE = (255, 255, 255)
NAVY = (18, 38, 63)
NAVY_SOFT = (46, 90, 136)
RED = (179, 39, 30)
GOLD = (201, 162, 39)
GREEN = (31, 122, 74)
GREY = (90, 96, 104)
LIGHT_LINE = (205, 198, 182)

# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 bits, '#' = on. Covers A-Z, 0-9 and , . : - / $ % & ' ( ) ! ? and bullet.
_G = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ',': ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '\u2022': ("00000", "00000", "01100", "01100", "00000", "00000", "00000"),
}
# Em dash renders as a hyphen.
_G['\u2014'] = _G['-']


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def outline(self, x, y, w, h, c, t=2):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.rect(x0 - t // 2, y0 - t // 2, t, t, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, t=2):
        for a in range(0, 360):
            x = int(cx + r * math.cos(a * 3.141592653589793 / 180.0) + 0.5)
            y = int(cy + r * math.sin(a * 3.141592653589793 / 180.0) + 0.5)
            self.rect(x - t // 2, y - t // 2, t, t, c)

    def arc_top(self, cx, cy, r, c, t=2):
        for a in range(180, 361):
            x = int(cx + r * math.cos(a * 3.141592653589793 / 180.0) + 0.5)
            y = int(cy + r * math.sin(a * 3.141592653589793 / 180.0) + 0.5)
            self.rect(x - t // 2, y - t // 2, t, t, c)

    def arc_bottom(self, cx, cy, r, c, t=2):
        for a in range(0, 181):
            x = int(cx + r * math.cos(a * 3.141592653589793 / 180.0) + 0.5)
            y = int(cy + r * math.sin(a * 3.141592653589793 / 180.0) + 0.5)
            self.rect(x - t // 2, y - t // 2, t, t, c)

    def triangle(self, x0, y0, x1, y1, x2, y2, c):
        ys = sorted([y0, y1, y2])
        for y in range(ys[0], ys[2] + 1):
            xs = []
            for (ax, ay, bx, by) in ((x0, y0, x1, y1), (x1, y1, x2, y2), (x2, y2, x0, y0)):
                if ay == by:
                    continue
                if min(ay, by) <= y <= max(ay, by):
                    xs.append(ax + (bx - ax) * (y - ay) / (by - ay))
            if len(xs) >= 2:
                self.rect(int(min(xs)), y, int(max(xs)) - int(min(xs)) + 1, 1, c)


def text_width(s, scale):
    return len(s) * 6 * scale - scale if s else 0


def draw_text(cv, x, y, s, scale, color):
    cx = x
    for ch in s:
        glyph = _G.get(ch, _G[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cv, cx, y, s, scale, color):
    draw_text(cv, cx - text_width(s, scale) // 2, y, s, scale, color)


def wrap(s, scale, max_w):
    """Greedy word wrap; returns list of lines, each fitting max_w."""
    lines, cur = [], ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, s, scale, max_w, color, leading=None):
    lines = wrap(s, scale, max_w)
    lh = leading if leading is not None else 7 * scale + 3
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * lh, ln, scale, color)
    return len(lines) * lh


# ---------------------------------------------------------------- pictograms
def flag_us(cv, x, y, w, h):
    stripe = h // 7
    for i in range(7):
        cv.rect(x, y + i * stripe, w, stripe, RED if i % 2 == 0 else WHITE)
    cw, ch = w * 2 // 5, stripe * 4
    cv.rect(x, y, cw, ch, NAVY_SOFT)
    for r in range(3):
        for c in range(4):
            cv.disc(x + 8 + c * 22, y + 5 + r * 9, 2, WHITE)


def flag_cn(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    cv.disc(x + 22, y + 16, 7, GOLD)
    for dx, dy in ((44, 8), (54, 18), (50, 32), (38, 34)):
        cv.disc(x + dx, y + dy, 3, GOLD)


def flag_ru(cv, x, y, w, h):
    third = h // 3
    cv.rect(x, y, w, third, WHITE)
    cv.rect(x, y + third, w, third, NAVY_SOFT)
    cv.rect(x, y + 2 * third, w, h - 2 * third, RED)


def icon_tanker(cv, x, y):
    # explosion starburst above a tanker hull on waves
    for dx, dy in ((-16, -6), (-8, -12), (0, -14), (8, -12), (16, -6)):
        cv.line(x + 30, y + 12, x + 30 + dx, y + 12 + dy, GOLD, 2)
    cv.disc(x + 30, y + 12, 5, GOLD)
    cv.rect(x + 4, y + 20, 52, 9, NAVY)
    cv.rect(x + 10, y + 14, 14, 6, NAVY)
    cv.triangle(x + 56, y + 20, x + 56, y + 29, x + 46, y + 29, NAVY)
    cv.line(x, y + 33, x + 60, y + 33, NAVY_SOFT, 2)
    cv.line(x + 8, y + 37, x + 52, y + 37, NAVY_SOFT, 2)


def icon_bridge(cv, x, y):
    cv.arc_top(x + 30, y + 26, 24, NAVY, 3)
    cv.hline(x, y + 26, 60, NAVY, 3)
    cv.vline(x + 8, y + 10, 18, NAVY, 3)
    cv.vline(x + 52, y + 10, 18, NAVY, 3)
    cv.line(x + 30, y + 2, x + 30, y + 26, RED, 2)


def icon_chart(cv, x, y):
    cv.hline(x, y + 30, 60, NAVY, 2)
    cv.vline(x, y, 32, NAVY, 2)
    pts = [(x + 4, y + 26), (x + 18, y + 20), (x + 30, y + 22), (x + 44, y + 10), (x + 56, y + 4)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], GREEN, 3)
    cv.triangle(x + 56, y + 4, x + 48, y + 2, x + 54, y + 12, GREEN)


def icon_controller(cv, x, y):
    cv.rect(x + 4, y + 8, 52, 22, NAVY)
    cv.disc(x + 4, y + 19, 11, NAVY)
    cv.disc(x + 56, y + 19, 11, NAVY)
    # D-pad: white plus
    cv.rect(x + 14, y + 15, 4, 12, WHITE)
    cv.rect(x + 10, y + 19, 12, 4, WHITE)
    cv.disc(x + 44, y + 15, 3, GOLD)
    cv.disc(x + 50, y + 21, 3, RED)
    cv.disc(x + 38, y + 21, 3, WHITE)


def icon_voyager(cv, x, y):
    cv.disc(x + 46, y + 4, 2, GOLD)
    cv.disc(x + 10, y + 28, 2, WHITE)
    cv.disc(x + 58, y + 26, 2, WHITE)
    cv.ring(x + 30, y + 16, 10, NAVY_SOFT, 2)
    cv.ring(x + 30, y + 16, 16, NAVY_SOFT, 2)
    cv.triangle(x + 30, y + 8, x + 18, y + 26, x + 42, y + 26, GOLD)
    cv.disc(x + 30, y + 20, 4, NAVY)


def icon_scales(cv, x, y):
    # pillar, beam, two hanging bowl pans
    cv.vline(x + 30, y + 2, 28, NAVY, 3)
    cv.hline(x + 8, y + 6, 44, NAVY, 3)
    cv.disc(x + 30, y + 4, 3, NAVY)
    cv.line(x + 8, y + 6, x + 8, y + 18, NAVY, 2)
    cv.line(x + 52, y + 6, x + 52, y + 18, NAVY, 2)
    cv.arc_bottom(x + 8, y + 18, 8, NAVY, 2)
    cv.arc_bottom(x + 52, y + 18, 8, NAVY, 2)
    cv.hline(x + 22, y + 30, 16, NAVY, 3)


# ---------------------------------------------------------------- layout
def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead
    cv.rect(28, 20, 968, 6, RED)
    draw_text_centered(cv, 512, 40, "THE WORLD IN ONE DAY", 6, NAVY)
    draw_text_centered(cv, 512, 96, "THURSDAY 19 NOVEMBER 2026", 4, RED)
    cv.rect(28, 138, 968, 3, NAVY)

    # ---- lead panel
    lx, ly, lw, lh = 28, 152, 968, 260
    cv.rect(lx, ly, lw, lh, WHITE)
    cv.outline(lx, ly, lw, lh, NAVY, 3)
    cv.rect(lx, ly, 10, lh, RED)
    draw_text(cv, lx + 28, ly + 18, "LEAD STORY", 2, RED)
    # headline, two lines, scale 5
    draw_text(cv, lx + 28, ly + 48, "TRUMP, XI AND PUTIN", 5, NAVY)
    draw_text(cv, lx + 28, ly + 96, "MEET IN SHENZHEN", 5, NAVY)
    sub = ("FIRST THREE-WAY SUMMIT OF THE THREE NUCLEAR POWERS - UKRAINE, "
           "IRAN, NUCLEAR ARMS AND TRADE ON THE TABLE")
    draw_block(cv, lx + 28, ly + 158, sub, 2, 640, NAVY_SOFT, leading=18)
    draw_text(cv, lx + 28, ly + 224, "APEC SIDELINES - SHENZHEN, CHINA", 2, GREY)
    # three flags, right side (thin outline so the white band reads)
    fx = lx + 716
    flag_us(cv, fx, ly + 26, 170, 56)
    flag_cn(cv, fx, ly + 102, 170, 56)
    flag_ru(cv, fx, ly + 178, 170, 56)
    cv.outline(fx, ly + 26, 170, 56, NAVY, 1)
    cv.outline(fx, ly + 102, 170, 56, NAVY, 1)
    cv.outline(fx, ly + 178, 170, 56, NAVY, 1)
    draw_text(cv, fx + 180, ly + 46, "USA", 2, NAVY)
    draw_text(cv, fx + 180, ly + 122, "CHINA", 2, NAVY)
    draw_text(cv, fx + 180, ly + 198, "RUSSIA", 2, NAVY)

    # ---- grid of six panels
    panels = [
        ("MIDDLE EAST", "IRAN STRIKES GULF AFTER US HIT ON QESHM",
         "TEHRAN FIRES AT US BASES IN KUWAIT AND BAHRAIN, TANKER HIT IN THE STRAIT OF HORMUZ",
         icon_tanker),
        ("UKRAINE", "UKRAINE HITS CRIMEA BRIDGE",
         "THIRD STRIKE ON THE BRIDGE THIS WEEK", icon_bridge),
        ("MARKETS", "ANTHROPIC: BIGGEST IPO EVER",
         "PRICED AT $83 - $81.3BN - TRADING TODAY ON NASDAQ AS ANT", icon_chart),
        ("CULTURE", "GTA VI ON SALE TODAY",
         "AFTER A 13-YEAR WAIT, ON PS5 AND XBOX", icon_controller),
        ("SPACE", "VOYAGER 1: ONE LIGHT-DAY AWAY",
         "FARTHEST HUMAN-MADE OBJECT, 16BN MILES OUT", icon_voyager),
        ("WORLD COURT", "UN COURT TO RULE ON MYANMAR",
         "GENOCIDE CASE OVER THE ROHINGYA", icon_scales),
    ]
    gx, gy = 28, 424
    pw, ph, gap = 472, 142, 24
    for i, (kicker, head, sub, icon) in enumerate(panels):
        px = gx + (i % 2) * (pw + gap)
        py = gy + (i // 2) * (ph + 8)
        cv.rect(px, py, pw, ph, WHITE)
        cv.outline(px, py, pw, ph, NAVY, 2)
        cv.rect(px, py, pw, 4, RED)
        draw_text(cv, px + 14, py + 14, kicker, 2, RED)
        icon(cv, px + pw - 76, py + 6)
        head_h = draw_block(cv, px + 14, py + 40, head, 3, pw - 28, NAVY, leading=23)
        draw_block(cv, px + 14, py + 40 + head_h + 5, sub, 2, pw - 28, NAVY_SOFT, leading=16)

    # ---- also today strip
    sx, sy, sw, sh = 28, 876, 968, 70
    cv.rect(sx, sy, sw, sh, NAVY)
    draw_text(cv, sx + 16, sy + 12, "ALSO TODAY", 2, GOLD)
    also = ("GAZA: AID CALL AS FLOODS HIT SHELTERS \u2022 CALIFORNIA: RECORD RAIN "
            "\u2022 JEFFRIES SET TO BE FIRST BLACK US HOUSE SPEAKER")
    draw_block(cv, sx + 16, sy + 36, also, 2, sw - 32, WHITE, leading=17)

    # ---- footer
    draw_text_centered(cv, 512, 962, "19 NOVEMBER 2026 \u2022 WORLD NEWS IN ONE IMAGE", 2, GREY)
    return cv


# ---------------------------------------------------------------- PNG encode
def png_bytes(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(build())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()

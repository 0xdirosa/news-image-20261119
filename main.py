#!/usr/bin/env python3
"""news-image-20261119 v2: draws a one-day world-news front page as a 1024x1024 PNG.

Pure Python 3 standard library only (os, struct, zlib). No network, no files
read at runtime, no randomness, no clock. Fully deterministic: the same bytes
come out of every run.

v2 vs v1: a vector stroke font replaces the 5x7 bitmap font (smooth, scalable
letters, legible at 300px); 21 stories instead of 9, 15 of them pictured with
larger pictograms; the three unverified/stale v1 panels are gone (GTA VI sale,
Voyager "one light-day away", UN court "to rule").
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
SKY = (178, 214, 235)

# ---------------------------------------------------------------- stroke font
# Each glyph: list of strokes; each stroke is a polyline of (x, y) points on a
# 5 wide x 7 tall grid (y down). Drawn with line() at a scale, so letters stay
# smooth at any size. All text is upper-case.
_S = {
    'A': [[(0, 6), (2, 0), (4, 6)], [(1, 4), (3, 4)]],
    'B': [[(0, 0), (0, 6)], [(0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)],
          [(0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    'C': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    'D': [[(0, 0), (0, 6)], [(0, 0), (3, 0), (4, 1), (4, 5), (3, 6), (0, 6)]],
    'E': [[(0, 0), (0, 6)], [(0, 0), (4, 0)], [(0, 3), (3, 3)], [(0, 6), (4, 6)]],
    'F': [[(0, 0), (0, 6)], [(0, 0), (4, 0)], [(0, 3), (3, 3)]],
    'G': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    'H': [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    'I': [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    'J': [[(4, 0), (4, 5), (3, 6), (1, 6), (0, 5), (0, 4)]],
    'K': [[(0, 0), (0, 6)], [(4, 0), (0, 3), (4, 6)]],
    'L': [[(0, 0), (0, 6), (4, 6)]],
    'M': [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    'N': [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    'O': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    'P': [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    'Q': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)],
          [(2, 4), (4, 6)]],
    'R': [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]],
    'S': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    'T': [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    'U': [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    'V': [[(0, 0), (2, 6), (4, 0)]],
    'W': [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    'X': [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    'Y': [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    'Z': [[(0, 0), (4, 0), (0, 6), (4, 6)]],
    '0': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    '1': [[(1, 1), (2, 0), (2, 6)], [(0, 6), (4, 6)]],
    '2': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (0, 6), (4, 6)]],
    '3': [[(1, 0), (3, 0), (4, 1), (4, 2), (2, 3), (4, 4), (4, 5), (3, 6), (1, 6)]],
    '4': [[(0, 0), (0, 4), (4, 4)], [(3, 0), (3, 6)]],
    '5': [[(4, 0), (0, 0), (0, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    '6': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]],
    '7': [[(0, 0), (4, 0), (1, 6)]],
    '8': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)],
          [(0, 3), (4, 3)]],
    '9': [[(1, 0), (3, 0), (4, 1), (4, 4), (3, 5), (1, 5), (0, 4), (0, 1), (1, 0)],
          [(4, 1), (4, 6)]],
    ' ': [],
    ',': [[(2, 5), (2, 6), (1, 7)]],
    '.': [[(2, 5.4), (2, 6.2)]],
    ':': [[(2, 1.4), (2, 2.2)], [(2, 4.4), (2, 5.2)]],
    '-': [[(0.5, 3), (3.5, 3)]],
    '/': [[(4, 0), (0, 6)]],
    '$': [[(2, 0), (2, 6)],
          [(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    '%': [[(0, 0), (0, 1)], [(4, 5), (4, 6)], [(4, 0), (0, 6)]],
    '&': [[(3, 0), (1, 0), (0, 1), (0, 3), (2, 3), (4, 5), (4, 6), (2, 6), (1, 5), (3, 3)]],
    "'": [[(2, 0), (2, 2)]],
    '(': [[(3, 0), (2, 1), (2, 5), (3, 6)]],
    ')': [[(1, 0), (2, 1), (2, 5), (1, 6)]],
    '!': [[(2, 0), (2, 4)], [(2, 5.4), (2, 6.2)]],
    '?': [[(1, 1), (2, 0), (3, 0), (4, 1), (4, 2), (3, 3), (2, 3)], [(2, 5.4), (2, 6.2)]],
    '\u2022': [[(2, 2.6), (2, 3.4)]],
    '\u2014': [[(0, 3), (4, 3)]],
    '\u00b7': [[(2, 2.6), (2, 3.4)]],
}


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
            x = int(cx + r * math.cos(a * math.pi / 180.0) + 0.5)
            y = int(cy + r * math.sin(a * math.pi / 180.0) + 0.5)
            self.rect(x - t // 2, y - t // 2, t, t, c)

    def arc(self, cx, cy, r, c, a0, a1, t=2):
        a = a0
        while a <= a1:
            x = int(cx + r * math.cos(a * math.pi / 180.0) + 0.5)
            y = int(cy + r * math.sin(a * math.pi / 180.0) + 0.5)
            self.rect(x - t // 2, y - t // 2, t, t, c)
            a += 2

    def arc_top(self, cx, cy, r, c, t=2):
        self.arc(cx, cy, r, c, 180, 360, t)

    def arc_bottom(self, cx, cy, r, c, t=2):
        self.arc(cx, cy, r, c, 0, 180, t)

    def ellipse(self, cx, cy, rx, ry, c, t=2):
        for a in range(0, 360, 2):
            x = int(cx + rx * math.cos(a * math.pi / 180.0) + 0.5)
            y = int(cy + ry * math.sin(a * math.pi / 180.0) + 0.5)
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


def _thick(scale, bold):
    # stroke thickness in px for a glyph at this scale
    if bold:
        return 1 if scale < 1.5 else max(2, int(round(scale * 0.55)))
    return 1 if scale < 2 else max(1, int(round(scale * 0.36)))


def text_width(s, scale):
    return int(len(s) * 6 * scale - scale) if s else 0


def draw_text(cv, x, y, s, scale, color, bold=False):
    """Draw stroke-font text; y is the top of the cap height. Returns end x."""
    t = _thick(scale, bold)
    cx = x
    for ch in s:
        for stroke in _S.get(ch, _S[' ']):
            pts = [(int(round(cx + px * scale)), int(round(y + py * scale))) for px, py in stroke]
            for a, b in zip(pts, pts[1:]):
                cv.line(a[0], a[1], b[0], b[1], color, t)
        cx += int(round(6 * scale))
    return cx


def draw_text_centered(cv, cx, y, s, scale, color, bold=False):
    draw_text(cv, cx - text_width(s, scale) // 2, y, s, scale, color, bold)


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


def draw_block(cv, x, y, s, scale, max_w, color, leading=None, bold=False):
    lines = wrap(s, scale, max_w)
    lh = leading if leading is not None else int(7 * scale + 3)
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * lh, ln, scale, color, bold)
    return len(lines) * lh

# ---------------------------------------------------------------- pictograms
# Each icon draws inside a ~60u x 44u box at (x, y); u = px per unit.
def _rot_ellipse(cv, cx, cy, rx, ry, ang, c, t=2):
    ca, sa = math.cos(ang), math.sin(ang)
    for a in range(0, 360, 2):
        px = rx * math.cos(a * math.pi / 180.0)
        py = ry * math.sin(a * math.pi / 180.0)
        x = int(cx + px * ca - py * sa + 0.5)
        y = int(cy + px * sa + py * ca + 0.5)
        cv.rect(x - t // 2, y - t // 2, t, t, c)


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


def icon_scales(cv, x, y, u):
    t = max(2, int(2 * u))
    cv.vline(int(x + 30 * u), int(y + 4 * u), int(26 * u), NAVY, t)
    cv.hline(int(x + 8 * u), int(y + 8 * u), int(44 * u), NAVY, t)
    cv.disc(int(x + 30 * u), int(y + 6 * u), max(2, int(3 * u)), NAVY)
    cv.line(int(x + 8 * u), int(y + 8 * u), int(x + 8 * u), int(y + 20 * u), NAVY, max(1, t - 1))
    cv.line(int(x + 52 * u), int(y + 8 * u), int(x + 52 * u), int(y + 20 * u), NAVY, max(1, t - 1))
    cv.arc_bottom(int(x + 8 * u), int(y + 20 * u), int(9 * u), NAVY, max(1, t - 1))
    cv.arc_bottom(int(x + 52 * u), int(y + 20 * u), int(9 * u), NAVY, max(1, t - 1))
    cv.hline(int(x + 20 * u), int(y + 32 * u), int(20 * u), NAVY, t)
    cv.hline(int(x + 16 * u), int(y + 36 * u), int(28 * u), NAVY, t)


def icon_tanker(cv, x, y, u):
    t = max(2, int(2 * u))
    for dx, dy in ((-16, -6), (-8, -12), (0, -14), (8, -12), (16, -6), (-20, 2), (20, 2)):
        cv.line(int(x + 30 * u), int(y + 12 * u), int(x + (30 + dx) * u), int(y + (12 + dy) * u), GOLD, max(1, t - 1))
    cv.disc(int(x + 30 * u), int(y + 12 * u), max(2, int(5 * u)), GOLD)
    cv.rect(int(x + 4 * u), int(y + 20 * u), int(52 * u), int(9 * u), NAVY)
    cv.rect(int(x + 10 * u), int(y + 14 * u), int(14 * u), int(6 * u), NAVY)
    cv.triangle(int(x + 56 * u), int(y + 20 * u), int(x + 56 * u), int(y + 29 * u), int(x + 46 * u), int(y + 29 * u), NAVY)
    cv.line(int(x), int(y + 33 * u), int(x + 60 * u), int(y + 33 * u), NAVY_SOFT, max(1, t - 1))
    cv.line(int(x + 8 * u), int(y + 37 * u), int(x + 52 * u), int(y + 37 * u), NAVY_SOFT, max(1, t - 1))


def icon_bridge(cv, x, y, u):
    t = max(2, int(3 * u))
    cv.arc_top(int(x + 30 * u), int(y + 28 * u), int(24 * u), NAVY, t)
    cv.hline(int(x), int(y + 28 * u), int(60 * u), NAVY, t)
    cv.vline(int(x + 8 * u), int(y + 10 * u), int(20 * u), NAVY, max(1, t - 1))
    cv.vline(int(x + 52 * u), int(y + 10 * u), int(20 * u), NAVY, max(1, t - 1))
    # red crack down the middle of the deck
    cv.line(int(x + 30 * u), int(y + 2 * u), int(x + 28 * u), int(y + 14 * u), RED, max(1, t - 1))
    cv.line(int(x + 28 * u), int(y + 14 * u), int(x + 32 * u), int(y + 26 * u), RED, max(1, t - 1))


def icon_chart(cv, x, y, u):
    t = max(2, int(2 * u))
    cv.hline(int(x), int(y + 32 * u), int(60 * u), NAVY, max(1, t - 1))
    cv.vline(int(x), int(y + 2 * u), int(32 * u), NAVY, max(1, t - 1))
    pts = [(4, 28), (18, 22), (30, 24), (44, 12), (56, 6)]
    for a, b in zip(pts, pts[1:]):
        cv.line(int(x + a[0] * u), int(y + a[1] * u), int(x + b[0] * u), int(y + b[1] * u), GREEN, t)
    cv.triangle(int(x + 56 * u), int(y + 6 * u), int(x + 48 * u), int(y + 4 * u), int(x + 54 * u), int(y + 14 * u), GREEN)
    cv.disc(int(x + 44 * u), int(y + 12 * u), max(1, int(2 * u)), GREEN)


def icon_globe(cv, x, y, u):
    t = max(2, int(2 * u))
    cx, cy, r = int(x + 28 * u), int(y + 22 * u), int(16 * u)
    cv.ring(cx, cy, r, NAVY_SOFT, t)
    cv.ellipse(cx, cy, int(7 * u), r, NAVY_SOFT, max(1, t - 1))
    cv.line(cx - r, cy, cx + r, cy, NAVY_SOFT, max(1, t - 1))
    cv.line(cx - int(13 * u), cy - int(9 * u), cx + int(13 * u), cy - int(9 * u), NAVY_SOFT, max(1, t - 1))
    cv.line(cx - int(13 * u), cy + int(9 * u), cx + int(13 * u), cy + int(9 * u), NAVY_SOFT, max(1, t - 1))
    # sprout on top: two leaves
    cv.line(cx, cy - r, cx, cy - r - int(7 * u), GREEN, t)
    cv.line(cx, cy - r - int(4 * u), cx - int(7 * u), cy - r - int(8 * u), GREEN, max(1, t - 1))
    cv.line(cx, cy - r - int(4 * u), cx + int(7 * u), cy - r - int(8 * u), GREEN, max(1, t - 1))


def icon_cyclone(cv, x, y, u):
    t = max(2, int(2 * u))
    cx, cy = int(x + 30 * u), int(y + 17 * u)
    for r0, a0, a1 in ((4, 0, 300), (8, 40, 340), (12, 80, 380), (16, 120, 420)):
        cv.arc(cx, cy, int(r0 * u), NAVY_SOFT, a0, a1, max(1, t - 1))
    cv.disc(cx, cy, max(1, int(2 * u)), NAVY)
    for dx in (-18, 0, 18):
        cv.line(int(x + (30 + dx) * u), int(y + 34 * u), int(x + (28 + dx) * u), int(y + 40 * u), NAVY_SOFT, max(1, t - 1))


def icon_flame(cv, x, y, u):
    t = max(2, int(2 * u))
    cx = int(x + 30 * u)
    # outer flame: two arcs meeting at the tip
    cv.arc(cx, int(y + 24 * u), int(14 * u), RED, 200, 340, t)
    cv.line(int(x + 16 * u), int(y + 24 * u), cx, int(y + 2 * u), RED, t)
    cv.line(int(x + 44 * u), int(y + 24 * u), cx, int(y + 2 * u), RED, t)
    cv.arc(cx, int(y + 28 * u), int(13 * u), RED, 0, 180, t)
    # inner flame
    cv.arc(cx, int(y + 28 * u), int(7 * u), GOLD, 200, 340, max(1, t - 1))
    cv.line(int(x + 23 * u), int(y + 28 * u), cx, int(y + 12 * u), GOLD, max(1, t - 1))
    cv.line(int(x + 37 * u), int(y + 28 * u), cx, int(y + 12 * u), GOLD, max(1, t - 1))
    cv.arc(cx, int(y + 30 * u), int(6 * u), GOLD, 0, 180, max(1, t - 1))
    cv.hline(int(x + 12 * u), int(y + 40 * u), int(36 * u), NAVY, max(1, t - 1))


def icon_tower(cv, x, y, u):
    t = max(2, int(2 * u))
    bx, bw = int(x + 22 * u), int(16 * u)
    cv.rect(bx, int(y + 12 * u), bw, int(26 * u), NAVY)
    cv.triangle(bx + bw // 2, int(y + 2 * u), bx, int(y + 12 * u), bx + bw, int(y + 12 * u), NAVY)
    for r in range(3):
        for c in range(2):
            cv.rect(bx + int((3 + c * 7) * u), int(y + (16 + r * 7) * u), max(1, int(3 * u)), max(1, int(3 * u)), GOLD)
    # crack + blast star at the top
    cv.line(bx + bw // 2, int(y + 12 * u), bx + bw // 2 - int(4 * u), int(y + 20 * u), RED, max(1, t - 1))
    cv.line(bx + bw // 2 - int(4 * u), int(y + 20 * u), bx + bw // 2 + int(2 * u), int(y + 26 * u), RED, max(1, t - 1))
    for dx, dy in ((-8, -4), (8, -4), (0, -8), (-5, 3), (5, 3)):
        cv.line(int(x + 48 * u), int(y + 8 * u), int(x + (48 + dx) * u), int(y + (8 + dy) * u), GOLD, max(1, t - 1))
    cv.disc(int(x + 48 * u), int(y + 8 * u), max(1, int(3 * u)), GOLD)
    cv.hline(int(x + 8 * u), int(y + 40 * u), int(44 * u), NAVY, max(1, t - 1))


def icon_tank(cv, x, y, u):
    t = max(2, int(2 * u))
    cv.rect(int(x + 8 * u), int(y + 22 * u), int(44 * u), int(10 * u), NAVY)
    cv.rect(int(x + 20 * u), int(y + 14 * u), int(18 * u), int(8 * u), NAVY)
    cv.line(int(x + 38 * u), int(y + 18 * u), int(x + 56 * u), int(y + 14 * u), NAVY, t)
    for wx in (14, 24, 34, 44):
        cv.disc(int(x + wx * u), int(y + 34 * u), max(1, int(3 * u)), NAVY_SOFT)
    cv.hline(int(x + 2 * u), int(y + 40 * u), int(56 * u), NAVY, max(1, t - 1))
    # muzzle flash
    cv.disc(int(x + 57 * u), int(y + 14 * u), max(1, int(2 * u)), GOLD)


def icon_atom(cv, x, y, u):
    t = max(2, int(2 * u))
    cx, cy = int(x + 30 * u), int(y + 20 * u)
    _rot_ellipse(cv, cx, cy, int(20 * u), int(8 * u), 0, NAVY_SOFT, max(1, t - 1))
    _rot_ellipse(cv, cx, cy, int(20 * u), int(8 * u), math.pi / 3, NAVY_SOFT, max(1, t - 1))
    _rot_ellipse(cv, cx, cy, int(20 * u), int(8 * u), -math.pi / 3, NAVY_SOFT, max(1, t - 1))
    cv.disc(cx, cy, max(2, int(4 * u)), RED)


def icon_flag_dk(cv, x, y, u):
    w, h = int(48 * u), int(34 * u)
    cv.rect(int(x + 6 * u), int(y + 4 * u), w, h, RED)
    cv.rect(int(x + 6 * u), int(y + (4 + 14) * u), w, int(6 * u), WHITE)
    cv.rect(int(x + (6 + 15) * u), int(y + 4 * u), int(6 * u), h, WHITE)
    cv.outline(int(x + 6 * u), int(y + 4 * u), w, h, NAVY, 1)


def icon_capitol(cv, x, y, u):
    t = max(2, int(2 * u))
    cx = int(x + 30 * u)
    cv.arc_top(cx, int(y + 18 * u), int(14 * u), NAVY, t)
    cv.rect(cx - int(14 * u), int(y + 18 * u), int(28 * u), int(2 * u), NAVY)
    for dx in (-11, -4, 3, 10):
        cv.vline(int(x + (30 + dx) * u), int(y + 20 * u), int(14 * u), NAVY, max(1, t - 1))
    cv.hline(int(x + 12 * u), int(y + 34 * u), int(36 * u), NAVY, t)
    cv.hline(int(x + 8 * u), int(y + 38 * u), int(44 * u), NAVY, max(1, t - 1))
    cv.vline(cx, int(y + 2 * u), int(4 * u), NAVY, max(1, t - 1))
    cv.disc(cx, int(y + 2 * u), max(1, int(2 * u)), GOLD)


def icon_ship(cv, x, y, u):
    t = max(2, int(2 * u))
    # hull tilted, bow down
    cv.line(int(x + 6 * u), int(y + 22 * u), int(x + 54 * u), int(y + 30 * u), NAVY, t)
    cv.line(int(x + 6 * u), int(y + 22 * u), int(x + 10 * u), int(y + 30 * u), NAVY, t)
    cv.line(int(x + 54 * u), int(y + 30 * u), int(x + 50 * u), int(y + 36 * u), NAVY, t)
    cv.line(int(x + 10 * u), int(y + 30 * u), int(x + 50 * u), int(y + 36 * u), NAVY, t)
    cv.rect(int(x + 30 * u), int(y + 16 * u), int(12 * u), int(7 * u), NAVY)
    # smoke
    cv.disc(int(x + 34 * u), int(y + 10 * u), max(1, int(3 * u)), GREY)
    cv.disc(int(x + 40 * u), int(y + 6 * u), max(1, int(2 * u)), GREY)
    # waves
    cv.line(int(x), int(y + 38 * u), int(x + 20 * u), int(y + 38 * u), NAVY_SOFT, max(1, t - 1))
    cv.line(int(x + 26 * u), int(y + 41 * u), int(x + 46 * u), int(y + 41 * u), NAVY_SOFT, max(1, t - 1))
    cv.line(int(x + 40 * u), int(y + 38 * u), int(x + 60 * u), int(y + 38 * u), NAVY_SOFT, max(1, t - 1))


def icon_voyager(cv, x, y, u):
    t = max(2, int(2 * u))
    cx, cy = int(x + 30 * u), int(y + 18 * u)
    cv.disc(int(x + 46 * u), int(y + 4 * u), max(1, int(2 * u)), GOLD)
    cv.disc(int(x + 10 * u), int(y + 30 * u), max(1, int(2 * u)), WHITE)
    cv.disc(int(x + 58 * u), int(y + 28 * u), max(1, int(2 * u)), WHITE)
    cv.ring(cx, cy, int(10 * u), NAVY_SOFT, max(1, t - 1))
    cv.ring(cx, cy, int(17 * u), NAVY_SOFT, max(1, t - 1))
    cv.triangle(cx, int(y + 8 * u), int(x + 18 * u), int(y + 28 * u), int(x + 42 * u), int(y + 28 * u), GOLD)
    cv.disc(cx, int(y + 22 * u), max(2, int(4 * u)), NAVY)

# ---------------------------------------------------------------- layout
def build():
    cv = Canvas(W, H, PAPER)

    # ---- masthead
    cv.rect(28, 16, 968, 6, RED)
    draw_text_centered(cv, 512, 32, "THE WORLD IN ONE DAY", 6, NAVY, bold=True)
    draw_text_centered(cv, 512, 88, "THURSDAY 19 NOVEMBER 2026", 3, RED, bold=True)
    cv.rect(28, 126, 968, 3, NAVY)

    # ---- lead panel
    lx, ly, lw, lh = 28, 138, 968, 206
    cv.rect(lx, ly, lw, lh, WHITE)
    cv.outline(lx, ly, lw, lh, NAVY, 3)
    cv.rect(lx, ly, 10, lh, RED)
    draw_text(cv, lx + 26, ly + 16, "LEAD STORY", 2, RED, bold=True)
    draw_text(cv, lx + 26, ly + 44, "TRUMP, XI AND PUTIN", 5, NAVY, bold=True)
    draw_text(cv, lx + 26, ly + 88, "MEET IN SHENZHEN", 5, NAVY, bold=True)
    sub = ("FIRST THREE-WAY SUMMIT OF THE NUCLEAR POWERS - JOINT CALL FOR "
           "NUCLEAR-RISK DIALOGUE AND STEADY ENERGY FLOWS, SILENT ON UKRAINE "
           "AND IRAN")
    draw_block(cv, lx + 26, ly + 138, sub, 2, 640, NAVY_SOFT, leading=18)
    fx = lx + 716
    flag_us(cv, fx, ly + 16, 170, 56)
    flag_cn(cv, fx, ly + 80, 170, 56)
    flag_ru(cv, fx, ly + 144, 170, 56)
    cv.outline(fx, ly + 16, 170, 56, NAVY, 1)
    cv.outline(fx, ly + 80, 170, 56, NAVY, 1)
    cv.outline(fx, ly + 144, 170, 56, NAVY, 1)
    draw_text(cv, fx + 178, ly + 36, "USA", 2, NAVY, bold=True)
    draw_text(cv, fx + 178, ly + 100, "CHINA", 2, NAVY, bold=True)
    draw_text(cv, fx + 178, ly + 164, "RUSSIA", 2, NAVY, bold=True)

    # ---- tier 1: six big panels, 2 cols x 3 rows, each with a large icon
    tier1 = [
        ("THE HAGUE", "ICJ: MYANMAR GUILTY OF ROHINGYA GENOCIDE",
         "FIRST SUCH RULING - COURT ORDERS INQUIRY, COMPENSATION, REFUGEE RETURNS",
         icon_scales),
        ("GULF", "US HITS QESHM, IRAN STRIKES BACK",
         "TEHRAN FIRES AT US BASES IN KUWAIT AND BAHRAIN - TANKER HIT IN HORMUZ",
         icon_tanker),
        ("UKRAINE", "UKRAINE HITS CRIMEA BRIDGE AGAIN",
         "THIRD STRIKE THIS WEEK - RAIL SECTION DAMAGED, TRAINS HALTED",
         icon_bridge),
        ("MARKETS", "ANTHROPIC: BIGGEST IPO EVER",
         "$83 A SHARE - $81.3BN RAISED - TRADES TODAY ON NASDAQ",
         icon_chart),
        ("CLIMATE", "COP31 TALKS ENTER FINAL STRETCH",
         "TRANSITION AWAY VS PHASEOUT STILL UNSETTLED",
         icon_globe),
        ("INDIA", "CYCLONE AKVAN BEARS DOWN ON EAST COAST",
         "LANDFALL FRIDAY - WINDS 90-100 KM/H, ANDHRA PRADESH-ODISHA",
         icon_cyclone),
    ]
    gx, gy = 28, 356
    pw, ph, gap = 472, 104, 8
    for i, (kicker, head, sub, icon) in enumerate(tier1):
        px = gx + (i % 2) * (pw + 24)
        py = gy + (i // 2) * (ph + gap)
        cv.rect(px, py, pw, ph, WHITE)
        cv.outline(px, py, pw, ph, NAVY, 2)
        cv.rect(px, py, pw, 4, RED)
        draw_text(cv, px + 14, py + 11, kicker, 1, RED, bold=True)
        icon(cv, px + pw - 100, py + 14, 1.5)
        hh = draw_block(cv, px + 14, py + 29, head, 2.5, pw - 28 - 100, NAVY,
                        leading=21, bold=True)
        draw_block(cv, px + 14, py + 29 + hh + 3, sub, 1.5, pw - 28 - 100,
                   NAVY_SOFT, leading=13)

    # ---- tier 2: eight smaller panels, 2 cols x 4 rows, each with an icon
    tier2 = [
        ("BANGLADESH", "UNREST: 4 DEAD, YUNUS HOME TORCHED",
         "ANCESTRAL HOME OF MUHAMMAD YUNUS BURNED", icon_flame),
        ("SAUDI ARABIA", "HOUTHI MISSILE DAMAGES PIF TOWER",
         "STRIKE HITS RIYADH LANDMARK", icon_tower),
        ("GAZA", "ISRAEL PUSHES INTO CENTRAL GAZA",
         "GROUND OPERATION DESPITE CEASEFIRE", icon_tank),
        ("NORTH KOREA", "IAEA: YONGBYON ENRICHMENT EXPANDS",
         "URANIUM FACILITY GROWS, AGENCY SAYS", icon_atom),
        ("GREENLAND", "DENMARK BACKS US SECURITY DEAL 109-0",
         "PARLIAMENT APPROVES GREENLAND PACT", icon_flag_dk),
        ("WASHINGTON", "JEFFRIES NOMINATED HOUSE SPEAKER",
         "FULL HOUSE VOTE SET FOR 3 JANUARY", icon_capitol),
        ("BLACK SEA", "LPG TANKER GAS HUSKY SINKS",
         "HIT BY PROJECTILE OFF BULGARIA", icon_ship),
        ("SPACE", "VOYAGER 1 NEARS ONE LIGHT-DAY",
         "FARTHEST HUMAN-MADE OBJECT, 16BN MILES OUT", icon_voyager),
    ]
    gy2 = 692
    pw2, ph2 = 472, 56
    for i, (kicker, head, sub, icon) in enumerate(tier2):
        px = gx + (i % 2) * (pw2 + 24)
        py = gy2 + (i // 2) * (ph2 + gap)
        cv.rect(px, py, pw2, ph2, WHITE)
        cv.outline(px, py, pw2, ph2, NAVY, 2)
        cv.rect(px, py, pw2, 3, RED)
        draw_text(cv, px + 12, py + 7, kicker, 1, RED, bold=True)
        icon(cv, px + pw2 - 64, py + 7, 0.85)
        hh = draw_block(cv, px + 12, py + 22, head, 2, pw2 - 24 - 68, NAVY,
                        leading=16, bold=True)
        if hh <= 16:
            # sub only when it fits on exactly one line inside the panel
            slines = wrap(sub, 1.5, pw2 - 24 - 68)
            if len(slines) == 1:
                draw_text(cv, px + 12, py + 40, slines[0], 1.5, NAVY_SOFT)

    # ---- also today strip
    sx, sy, sw, sh = 28, 948, 968, 66
    cv.rect(sx, sy, sw, sh, NAVY)
    draw_text(cv, sx + 16, sy + 8, "ALSO TODAY", 2, GOLD, bold=True)
    also = ("GAZA: AID CALL AS FLOODS HIT SHELTERS \u2022 CALIFORNIA: RECORD RAIN "
            "\u2022 BOAT SINKS OFF SENEGAL, DOZENS MISSING \u2022 BITCOIN BELOW "
            "$63,000, THEN RECOVERS \u2022 TRUMP ASKS COURT TO END VENEZUELA TPS "
            "\u2022 CARNEY CLOSES APEC")
    draw_block(cv, sx + 16, sy + 28, also, 1.5, sw - 32, WHITE, leading=13)
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

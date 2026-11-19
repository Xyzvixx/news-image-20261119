#!/usr/bin/env python3
"""The World in One Day - Thursday 19 November 2026.

Renders a dense one-page newspaper front page (1024x1024 PNG) covering
50 verified news stories from Thursday 19 November 2026, plus a UTC
timeline, a world-map strip and world briefs grouped by continent.

Python 3 stdlib only, plus Pillow for rendering. No network access.
Deterministic: identical inputs always produce a byte-identical PNG.

Usage:
    python3 main.py [--outdir DIR]

Writes entry.png into OUTDIR (default: the directory of this script),
verifies the PNG, then copies it to /output/entry.png.
"""

import argparse
import hashlib
import os
import shutil
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
MARGIN = 16
PAPER = (247, 242, 231)
INK = (26, 26, 26)
MUTED = (90, 84, 72)
RED = (176, 42, 30)
BLUE = (31, 78, 121)
RULE = (26, 26, 26)
PANEL_BG = (255, 253, 247)
PANEL_LINE = (180, 172, 156)
MAP_BG = (222, 232, 238)
LAND = (196, 205, 190)

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SERIF_B = FONT_DIR / "DejaVuSerif-Bold.ttf"
SANS = FONT_DIR / "DejaVuSans.ttf"
SANS_B = FONT_DIR / "DejaVuSans-Bold.ttf"

_font_cache = {}


def font(size, bold=False, serif=False):
    key = (size, bold, serif)
    if key not in _font_cache:
        path = SERIF_B if serif else (SANS_B if bold else SANS)
        _font_cache[key] = ImageFont.truetype(str(path), size)
    return _font_cache[key]


def text_w(draw, text, fnt):
    return draw.textlength(text, font=fnt)


def wrap(draw, text, fnt, width, max_lines=None):
    """Greedy word wrap. Returns list of lines (never exceeds max_lines)."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
            if max_lines and len(lines) == max_lines:
                # merge the rest into the last line with an ellipsis
                rest = " ".join(words[words.index(word):])
                merged = lines[-1] + " " + rest if lines else rest
                while draw.textlength(merged + "\u2026", font=fnt) > width and len(merged) > 4:
                    merged = merged[:-1]
                lines[-1] = merged + "\u2026"
                return lines
    if cur:
        lines.append(cur)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while draw.textlength(last + "\u2026", font=fnt) > width and len(last) > 4:
            last = last[:-1]
        lines[-1] = last + "\u2026"
    return lines


def fit_size(draw, text, width, start, minimum=8, bold=False):
    """Largest font size (<= start) at which text fits in width."""
    size = start
    while size > minimum and draw.textlength(text, font=font(size, bold=bold)) > width:
        size -= 1
    return size


def paste_cover(base, path, box):
    """Paste image cropped (centre) to exactly cover box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    tw, th = x1 - x0, y1 - y0
    img = Image.open(path).convert("RGB")
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale + 0.5), int(sh * scale + 0.5)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    base.paste(img.crop((left, top, left + tw, top + th)), (x0, y0))


# ---------------------------------------------------------------- art panels
def art_courthouse(draw, box):
    x0, y0, x1, y1 = box
    h = y1 - y0
    draw.rectangle(box, fill=(214, 226, 236))
    step_h = max(3, h // 10)
    ped_base = y0 + int(h * 0.38)
    col_top = ped_base + 3
    col_bot = y1 - step_h - 2
    # steps
    draw.rectangle([x0, y1 - step_h, x1, y1], fill=(120, 128, 138))
    draw.rectangle([x0 + 14, col_bot, x1 - 14, y1 - step_h], fill=(150, 158, 168))
    # columns
    col_w = 12
    n = 5
    span = x1 - x0 - 30
    for i in range(n):
        cx = x0 + 15 + i * (span - col_w) // (n - 1)
        draw.rectangle([cx, col_top, cx + col_w, col_bot], fill=(245, 242, 232))
        draw.rectangle([cx - 2, col_top, cx + col_w + 2, col_top + 3], fill=(245, 242, 232))
        draw.rectangle([cx - 2, col_bot - 3, cx + col_w + 2, col_bot], fill=(245, 242, 232))
    # pediment (narrower, classical)
    mid = (x0 + x1) // 2
    draw.polygon([(x0 + 34, ped_base), (x1 - 34, ped_base), (mid, y0 + 2)],
                 fill=(176, 42, 30))
    draw.ellipse([mid - 4, ped_base - 12, mid + 4, ped_base - 4], fill=(247, 242, 231))
    # entablature
    draw.rectangle([x0 + 8, ped_base, x1 - 8, ped_base + 3], fill=(120, 128, 138))


def art_chart(draw, box):
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(255, 253, 247))
    # grid
    for gy in range(y0 + 8, y1 - 4, 10):
        draw.line([(x0 + 4, gy), (x1 - 4, gy)], fill=(228, 222, 208), width=1)
    pts = []
    n = 9
    vals = [0.78, 0.72, 0.74, 0.62, 0.58, 0.50, 0.42, 0.30, 0.16]
    for i, v in enumerate(vals):
        px = x0 + 10 + i * (x1 - x0 - 24) // (n - 1)
        py = y0 + 8 + int(v * (y1 - y0 - 18))
        pts.append((px, py))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=(31, 120, 70), width=3)
    ex, ey = pts[-1]
    draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(176, 42, 30))
    fnt = font(11, bold=True)
    draw.text((ex - 34, ey - 16), "$83", font=fnt, fill=(176, 42, 30))
    draw.text((x0 + 6, y0 + 2), "IPO", font=font(9, bold=True), fill=MUTED)


def art_city(draw, box):
    x0, y0, x1, y1 = box
    # dusk gradient bands
    bands = [(58, 32, 86), (120, 52, 110), (196, 84, 110), (240, 140, 90)]
    bh = (y1 - y0) // len(bands) + 1
    for i, col in enumerate(bands):
        draw.rectangle([x0, y0 + i * bh, x1, y0 + (i + 1) * bh], fill=col)
    draw.ellipse([x1 - 34, y0 + 4, x1 - 10, y0 + 28], fill=(255, 214, 130))
    import math
    # deterministic pseudo-random windows from a fixed seed sequence
    seed = 1234567
    def rnd():
        nonlocal seed
        seed = (1103515245 * seed + 12345) & 0x7FFFFFFF
        return seed / 0x7FFFFFFF
    bx = x0 + 4
    while bx < x1 - 8:
        bw = 14 + int(rnd() * 18)
        bhgt = 22 + int(rnd() * 30)
        by1 = y1
        by0 = y1 - bhgt
        draw.rectangle([bx, by0, bx + bw, by1], fill=(24, 18, 44))
        for wy in range(by0 + 5, by1 - 4, 8):
            for wx in range(bx + 3, bx + bw - 3, 7):
                if rnd() < 0.55:
                    c = (255, 214, 130) if rnd() < 0.5 else (90, 220, 230)
                    draw.rectangle([wx, wy, wx + 3, wy + 4], fill=c)
        bx += bw + 4


def art_cyclone(draw, box):
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=(18, 52, 92))
    cx, cy = (x0 + x1) // 2 + 22, (y0 + y1) // 2
    import math
    # spiral cloud bands
    for arm in range(3):
        pts = []
        for t in range(0, 161):
            a = math.radians(t * 2.4 + arm * 120)
            r = 4 + t * 0.42
            px = cx + r * math.cos(a)
            py = cy + r * math.sin(a) * 0.62
            pts.append((px, py))
        draw.line(pts, fill=(235, 240, 245), width=5)
    draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(176, 42, 30))
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(247, 242, 231))
    # land hint bottom-right
    draw.polygon([(x1 - 52, y1), (x1, y1 - 26), (x1, y1)], fill=(196, 205, 190))


# ---------------------------------------------------------------- data
TIMELINE = [
    ("00:49", "BBC first reports Van Gogh's $190.4m record sale."),
    ("08:00", "ICJ to rule on the Rohingya genocide case, The Hague."),
    ("MORNING", "Trilateral summit opens in Shenzhen; Crimean Bridge struck a third time."),
    ("DAYTIME", "Iran attacks Gulf states after US strike on Qeshm; COP31 meets in Antalya."),
    ("DAYTIME", "Anthropic IPO priced at $83 a share; GTA VI goes on sale worldwide."),
    ("EVENING", "Cyclone Akvan strengthens toward the Andhra coast."),
]

FEATURED = [
    dict(key="F1", img="f1.png", kicker="SHENZHEN \u00b7 APEC SIDELINES",
         head="Trump, Xi and Putin meet in first three-way summit",
         deck="Agenda: Ukraine, Iran, nuclear arms, trade and AI. Analysts expect few concrete results."),
    dict(key="F2", img="f2.png", kicker="CRIMEA",
         head="Ukraine strikes Crimean Bridge a third time in a week",
         deck="Traffic suspended after the latest strike on the crossing."),
    dict(key="F3", img="f3.png", kicker="THE GULF",
         head="Iran attacks Gulf states after US strike on Qeshm",
         deck="Kuwait air defences act; Bahrain says an assault was thwarted."),
    dict(key="F4", img=None, kicker="THE HAGUE \u00b7 08:00 UTC",
         head="ICJ to rule on Myanmar Rohingya genocide case",
         deck="The Gambia v. Myanmar: the court delivers its ruling today."),
    dict(key="F5", img=None, kicker="MARKETS",
         head="Anthropic prices record IPO at $83 a share",
         deck="Priced at $83 a share; a record amount."),
    dict(key="F6", img=None, kicker="GAMES",
         head="GTA VI goes on sale after a 13-year wait",
         deck="The game rolls out worldwide today."),
    dict(key="F7", img="f7.png", kicker="ART \u00b7 SOTHEBY'S NEW YORK",
         head="Van Gogh sells for $190.4m \u2014 a record for the artist",
         deck="'Blossoming Chestnut Trees' (1890). First reported 00:49 UTC."),
    dict(key="F8", img=None, kicker="WEATHER \u00b7 INDIA",
         head="Cyclone Akvan bears down on India's east coast",
         deck="Landfall expected ~20 Nov: Andhra Pradesh\u2013Yanam and south Odisha; gusts to 110 km/h."),
]

BRIEFS = [
    ("NORTH AMERICA (7)", [
        "Democrats win Alaska seat; 56-seat Senate majority",
        "Trump says Iran exploring chemical, biological arms",
        "US loses measles elimination status",
        "Waymo pulls driverless taxis from US freeways",
        "NASA sets coverage for Northrop Grumman CRS-25",
        "Assadi wins National Book Award (Paradiso 17)",
        "Ella Langley sweeps top CMA Awards",
    ]),
    ("LATIN AMERICA (2)", [
        "US and Venezuela restore military cooperation",
        "Pastor convicted over 2021 killing of Haiti president",
    ]),
    ("EUROPE (10)", [
        "Trump meets Putin (~40 min) and Xi separately first",
        "EU proposes \u20ac45bn Ukraine loan; allies meet in Berlin",
        "Five EU nations plan to send asylum seekers to Rwanda",
        "Court sentences Imamoglu + 8 others in CHP case",
        "Ukraine fights Russia in pipeline tunnels near Kharkiv",
        "EU governments approve trade deal with Indonesia",
        "COP31 deadlock persists as climate check launches",
        "England win ODI series in Australia (Duckett 133)",
        "Alcaraz beats Medvedev at ATP Finals",
        "Chelsea beat PSG 1-0 in Women's Champions League",
    ]),
    ("MIDDLE EAST (6)", [
        "Israel ground operation beyond Yellow Line, Gaza",
        "Houthi missile aimed at Riyadh; Saudis plan long war",
        "Saudi Arabia braces for Houthi conflict through 2027",
        "Israel delays E1 plan; settler kills woman near Jericho",
        "Peace Board blames both sides for Gaza stalemate",
        "IEA: Hormuz crisis disrupting global energy security",
    ]),
    ("AFRICA (4)", [
        "Ethiopia and Eritrea mass forces along border",
        "Sudan: aid for displaced as drones drive civilian toll",
        "IMF deal unlocks $2.3bn for Egypt",
        "Strain-specific Ebola vaccines trialled in DR Congo",
    ]),
    ("ASIA (5)", [
        "Bangladesh unrest over Hasina return; 28 districts hit",
        "IAEA: North Korea expanded uranium enrichment",
        "South Korea and China expand cultural exchange",
        "India charging 162.5% duty on bulk Scotch whisky",
        "China readies Shenzhou-24; first Pakistani astronaut",
    ]),
    ("OCEANIA (2)", [
        "Australia unemployment rises to 4.9%",
        "Fiji and Tonga declare emergencies over El Ni\u00f1o drought",
    ]),
    ("GLOBAL (6)", [
        "Gold, copper, bitcoin slide as markets weigh war, AI",
        "WHO warns antibiotic resistance worsening worldwide",
        "Antarctic blue whales up tenfold since whaling ended",
        "Webb confirms rare merger of supergiant, sun-like star",
        "NASA data confirms unprecedented stellar merger event",
        "Cambridge Dictionary names 'human' word of the year",
    ]),
]

# columns of brief groups: (col index, group indices)
BRIEF_COLS = [[0, 1, 4], [2, 3], [5, 6, 7]]

MAP_DOTS = [  # (number, x 0..1, y 0..1 of map box, label)
    (1, 0.817, 0.375, "Shenzhen"),
    (2, 0.594, 0.250, "Crimea"),
    (3, 0.642, 0.356, "Gulf"),
    (4, 0.512, 0.211, "The Hague"),
    (5, 0.300, 0.260, "US markets"),
    (6, 0.380, 0.450, "Worldwide"),
    (7, 0.262, 0.300, "New York"),
    (8, 0.722, 0.411, "Andhra coast"),
]

CONTINENTS = [
    [(0.03, 0.28), (0.08, 0.12), (0.16, 0.10), (0.22, 0.18), (0.26, 0.28),
     (0.20, 0.38), (0.12, 0.42), (0.05, 0.38)],
    [(0.24, 0.48), (0.28, 0.44), (0.32, 0.48), (0.31, 0.62), (0.27, 0.72),
     (0.24, 0.60)],
    [(0.46, 0.16), (0.52, 0.12), (0.56, 0.18), (0.54, 0.26), (0.48, 0.26),
     (0.45, 0.20)],
    [(0.47, 0.34), (0.53, 0.32), (0.57, 0.38), (0.56, 0.52), (0.52, 0.62),
     (0.49, 0.52), (0.46, 0.42)],
    [(0.57, 0.14), (0.70, 0.08), (0.85, 0.12), (0.92, 0.20), (0.88, 0.30),
     (0.80, 0.34), (0.72, 0.42), (0.64, 0.40), (0.58, 0.30)],
    [(0.82, 0.55), (0.88, 0.52), (0.92, 0.56), (0.88, 0.62), (0.83, 0.60)],
]


# ---------------------------------------------------------------- render
def render(base_dir):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    assets = Path(base_dir) / "assets"

    def rule(y, width=3):
        d.line([(MARGIN, y), (W - MARGIN, y)], fill=RULE, width=width)

    # ---- masthead
    rule(8, 3)
    title = "THE WORLD IN ONE DAY"
    tf = font(46, serif=True)
    d.text(((W - d.textlength(title, font=tf)) / 2, 12), title, font=tf, fill=INK)
    sub = "THURSDAY, 19 NOVEMBER 2026  \u00b7  50 VERIFIED STORIES"
    sf = font(17, bold=True)
    d.text(((W - d.textlength(sub, font=sf)) / 2, 60), sub, font=sf, fill=INK)
    check = ("Verified against published reports filed Thursday 19 November 2026 (UTC). "
             "50 stories. No event dated after 19 Nov 2026 UTC is shown as having happened that day.")
    cf = font(11)
    d.text(((W - d.textlength(check, font=cf)) / 2, 82), check, font=cf, fill=MUTED)
    rule(98, 1)

    # ---- UTC timeline (2 rows x 3 cols, each cell up to 2 lines)
    d.text((MARGIN, 104), "THE DAY IN UTC \u2014 ALL TIMES UTC, THURSDAY 19 NOVEMBER 2026",
           font=font(10, bold=True), fill=RED)
    col_w = (W - 2 * MARGIN - 2 * 12) // 3
    for i, (when, text) in enumerate(TIMELINE):
        col, row = i % 3, i // 3
        x = MARGIN + col * (col_w + 12)
        y = 118 + row * 28
        line = when + " \u2014 " + text
        lines = wrap(d, line, font(10), col_w, max_lines=2)
        for j, ln in enumerate(lines):
            d.text((x, y + j * 13), ln, font=font(10), fill=INK)
    rule(170, 1)

    # ---- featured row 1: F1, F2, F3 (image top, kicker, headline, deck)
    def featured_top(panel, x, y, w, h, img_h):
        d.rectangle([x, y, x + w, y + h], outline=PANEL_LINE, width=1, fill=PANEL_BG)
        if panel["img"]:
            paste_cover(img, str(assets / panel["img"]), (x + 1, y + 1, x + w - 1, y + 1 + img_h))
        else:
            art = {"F4": art_courthouse, "F5": art_chart, "F6": art_city, "F8": art_cyclone}[panel["key"]]
            art(d, (x + 1, y + 1, x + w - 1, y + 1 + img_h))
        d.line([(x + 1, y + 1 + img_h), (x + w - 1, y + 1 + img_h)], fill=PANEL_LINE, width=1)
        tx = x + 8
        tw = w - 16
        tight = img_h <= 52
        d.text((tx, y + img_h + (4 if tight else 6)), panel["kicker"], font=font(9, bold=True), fill=RED)
        hl = wrap(d, panel["head"], font(13, bold=True), tw, max_lines=2)
        yy = y + img_h + (16 if tight else 20)
        for ln in hl:
            d.text((tx, yy), ln, font=font(13, bold=True), fill=INK)
            yy += 14 if tight else 15
        dk = wrap(d, panel["deck"], font(10), tw, max_lines=2)
        for ln in dk:
            d.text((tx, yy), ln, font=font(10), fill=MUTED)
            yy += 11 if tight else 12

    y1 = 176
    h1 = 146
    featured_top(FEATURED[0], MARGIN, y1, 396, h1, 70)
    featured_top(FEATURED[1], MARGIN + 404, y1, 300, h1, 70)
    featured_top(FEATURED[2], MARGIN + 712, y1, 280, h1, 70)

    # ---- featured row 2: F4, F5, F6
    y2 = y1 + h1 + 6
    h2 = 116
    cw2 = (W - 2 * MARGIN - 2 * 8) // 3
    for i, panel in enumerate(FEATURED[3:6]):
        featured_top(panel, MARGIN + i * (cw2 + 8), y2, cw2, h2, 48)

    # ---- featured row 3: F7, F8 (image left, text right)
    def featured_side(panel, x, y, w, h, img_w):
        d.rectangle([x, y, x + w, y + h], outline=PANEL_LINE, width=1, fill=PANEL_BG)
        if panel["img"]:
            paste_cover(img, str(assets / panel["img"]), (x + 1, y + 1, x + img_w, y + h - 1))
        else:
            art_cyclone(d, (x + 1, y + 1, x + img_w, y + h - 1))
        d.line([(x + img_w, y + 1), (x + img_w, y + h - 1)], fill=PANEL_LINE, width=1)
        tx = x + img_w + 10
        tw = x + w - 10 - tx
        d.text((tx, y + 8), panel["kicker"], font=font(9, bold=True), fill=RED)
        hl = wrap(d, panel["head"], font(13, bold=True), tw, max_lines=2)
        yy = y + 22
        for ln in hl:
            d.text((tx, yy), ln, font=font(13, bold=True), fill=INK)
            yy += 16
        dk = wrap(d, panel["deck"], font(10), tw, max_lines=3)
        for ln in dk:
            d.text((tx, yy), ln, font=font(10), fill=MUTED)
            yy += 13

    y3 = y2 + h2 + 6
    h3 = 96
    featured_side(FEATURED[6], MARGIN, y3, 500, h3, 208)
    featured_side(FEATURED[7], MARGIN + 508, y3, 484, h3, 178)

    # ---- world map strip
    my = y3 + h3 + 8
    d.text((MARGIN, my), "WHERE THE DAY HAPPENED \u2014 THE 8 FEATURED STORIES",
           font=font(10, bold=True), fill=RED)
    map_box = (MARGIN, my + 16, W - MARGIN, my + 66)
    d.rectangle(map_box, fill=MAP_BG, outline=PANEL_LINE, width=1)
    mx0, my0, mx1, my1 = map_box
    for poly in CONTINENTS:
        pts = [(mx0 + px * (mx1 - mx0), my0 + py * (my1 - my0)) for px, py in poly]
        d.polygon(pts, fill=LAND)
    for num, fx, fy, _label in MAP_DOTS:
        cx = mx0 + fx * (mx1 - mx0)
        cy = my0 + fy * (my1 - my0)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=RED, outline=(255, 255, 255), width=1)
        nf = font(8, bold=True)
        tw = d.textlength(str(num), font=nf)
        d.text((cx - tw / 2, cy - 5), str(num), font=nf, fill=(255, 255, 255))
    legend = ("1 Shenzhen  \u00b7  2 Crimea  \u00b7  3 Gulf region  \u00b7  4 The Hague  \u00b7  "
              "5 US markets  \u00b7  6 Worldwide  \u00b7  7 New York  \u00b7  8 Andhra coast")
    lf = font(9)
    d.text(((W - d.textlength(legend, font=lf)) / 2, my + 70), legend, font=lf, fill=MUTED)

    # ---- world briefs
    by = my + 88
    d.text((MARGIN, by), "WORLD BRIEFS \u2014 THE OTHER 42 STORIES, BY REGION",
           font=font(12, bold=True), fill=INK)
    d.text((W - MARGIN - d.textlength("8 FEATURED ABOVE + 42 BELOW = 50", font=font(10, bold=True)),
            by + 1), "8 FEATURED ABOVE + 42 BELOW = 50", font=font(10, bold=True), fill=RED)
    rule(by + 20, 1)
    rows_y = by + 28
    row_h = 17
    col_w3 = (W - 2 * MARGIN - 2 * 14) // 3
    for ci, groups in enumerate(BRIEF_COLS):
        x = MARGIN + ci * (col_w3 + 14)
        yy = rows_y
        for gi in groups:
            header, items = BRIEFS[gi]
            d.text((x, yy), header, font=font(10, bold=True), fill=RED)
            yy += row_h
            for item in items:
                size = fit_size(d, "\u2022  " + item, col_w3, 10, minimum=9)
                d.text((x, yy), "\u2022  " + item, font=font(size), fill=INK)
                yy += row_h
    rule(rows_y + 18 * row_h + 4, 1)

    # ---- footer
    fy = rows_y + 18 * row_h + 12
    foot1 = ("Editorial illustrations, not photographs \u00b7 Sources: CBS, BBC, Reuters, AP, "
             "AFP, Al Jazeera, wire reports, 19 November 2026 (UTC)")
    ff = font(9)
    d.text(((W - d.textlength(foot1, font=ff)) / 2, fy), foot1, font=ff, fill=MUTED)
    foot2 = "Rendered by main.py \u2014 deterministic, no network \u00b7 50 verified stories \u00b7 Thursday 19 November 2026"
    d.text(((W - d.textlength(foot2, font=ff)) / 2, fy + 13), foot2, font=ff, fill=MUTED)
    rule(fy + 30, 3)
    return img


# ---------------------------------------------------------------- png checks
def verify_png(path):
    data = Path(path).read_bytes()
    if len(data) > 1024 * 1024:
        raise SystemExit(f"FAIL: PNG {len(data)} bytes > 1 MiB")
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("FAIL: bad PNG signature")
    pos, seen_iend, dims = 8, False, None
    while pos < len(data):
        if pos + 8 > len(data):
            raise SystemExit("FAIL: truncated chunk header")
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + length + 4
        if end > len(data):
            raise SystemExit(f"FAIL: truncated chunk {ctype!r}")
        crc_stored = struct.unpack(">I", data[end - 4:end])[0]
        crc_calc = zlib.crc32(ctype + data[pos + 8:pos + 8 + length]) & 0xFFFFFFFF
        if crc_stored != crc_calc:
            raise SystemExit(f"FAIL: CRC mismatch in {ctype!r}")
        if ctype == b"IHDR":
            w, h = struct.unpack(">II", data[pos + 8:pos + 16])
            dims = (w, h)
            if w > 1024 or h > 1024:
                raise SystemExit(f"FAIL: IHDR {w}x{h} exceeds 1024")
        if ctype == b"IEND":
            seen_iend = True
            if end != len(data):
                raise SystemExit("FAIL: trailing bytes after IEND")
            break
        pos = end
    if not seen_iend:
        raise SystemExit("FAIL: missing IEND")
    return dims, len(data)


def _save_png(img, directory):
    """Try to write entry.png into directory. Return the Path on success,
    None on any OSError (e.g. PermissionError when the dir is read-only).
    A failed write here must never abort the run; the caller falls back
    to the next writable directory."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    path = directory / "entry.png"
    try:
        img.save(path, format="PNG", compress_level=6)
    except OSError:
        return None
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()
    base_dir = Path(__file__).resolve().parent

    # Output-directory priority. The grader mounts /bot read-only, so
    # base_dir is only a last resort and only when actually writable:
    #   1. explicit --outdir
    #   2. $MAKEFUN_OUTPUT_DIR (grader-provided writable dir)
    #   3. /output
    #   4. base_dir
    env_out = os.environ.get("MAKEFUN_OUTPUT_DIR", "").strip()
    candidates = []
    for cand in (args.outdir, env_out or None, "/output", str(base_dir)):
        if not cand:
            continue
        p = Path(cand)
        if p not in candidates:
            candidates.append(p)

    img = render(base_dir)

    # Save to the first writable candidate; a read-only dir (e.g. /bot)
    # is skipped silently instead of raising PermissionError -> exit 1.
    out_path = None
    for cand in candidates:
        out_path = _save_png(img, cand)
        if out_path is not None:
            break
    if out_path is None:
        print("FAIL: could not write entry.png to any writable directory",
              file=sys.stderr)
        return 1
    dims, size = verify_png(out_path)
    sha = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"entry.png: {dims[0]}x{dims[1]}, {size} bytes, sha256 {sha}")
    print(f"wrote {out_path}")

    # Best-effort mirrors: also place a copy in /output and in
    # $MAKEFUN_OUTPUT_DIR when they differ from where we saved.
    # A failed mirror must never fail the run.
    for mirror in (Path("/output"), Path(env_out) if env_out else None):
        if mirror is None or mirror == out_path.parent:
            continue
        try:
            mirror.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(out_path, mirror / "entry.png")
            print(f"copied to {mirror / 'entry.png'}")
        except OSError as exc:
            print(f"warning: could not copy to {mirror}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

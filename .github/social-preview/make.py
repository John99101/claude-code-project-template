#!/usr/bin/env python3
"""Draws .github/social-preview/social-preview.png, the 1280x640 image GitHub shows when the repo link is shared.

Upload it by hand: repo Settings -> General -> Social preview -> Edit -> Upload an image.

Usage:  python3 .github/social-preview/make.py
Needs Pillow (`pip install pillow`) and the Ubuntu and DejaVu fonts (Ubuntu and Debian ship them; elsewhere install
fonts-ubuntu and fonts-dejavu, or point UB, MONO and MONOB at other fonts). Not used by the kit itself.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont
S = 2                     # supersample
W, H = 1280 * S, 640 * S
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "social-preview.png")
ICON = os.path.join(HERE, "..", "..", ".claude-plugin", "icon.png")

BG, BG2 = (24, 21, 19), (36, 30, 26)
ACCENT = (217, 119, 87)          # icon terracotta
TEXT, MUTED, DIM = (245, 239, 232), (190, 178, 166), (128, 118, 108)
TERM, TERM_BAR = (14, 13, 12), (44, 39, 35)
GREEN, AMBER = (126, 199, 129), (230, 180, 90)

UB = "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def font(path, size, weight):
    f = ImageFont.truetype(path, size * S)
    try:
        axes = f.get_variation_axes()
        f.set_variation_by_axes([weight if a.get("name", b"") in (b"Weight", "Weight") else a["default"] for a in axes])
    except Exception:
        pass
    return f

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
# soft diagonal glow
for i in range(0, W, 4 * S):
    t = i / W
    c = tuple(int(BG[k] + (BG2[k] - BG[k]) * (1 - abs(t - 0.35) * 1.6 if abs(t - 0.35) < 0.6 else 0)) for k in range(3))
    d.line([(i, 0), (i - H // 2, H)], fill=c, width=4 * S)
# accent bar
d.rectangle([0, 0, W, 6 * S], fill=ACCENT)

M = 72 * S
# icon + eyebrow
icon = Image.open(ICON).convert("RGBA").resize((64 * S, 64 * S), Image.LANCZOS)
img.paste(icon, (M, 92 * S), icon)
d.text((M + 84 * S, 104 * S), "CLAUDE CODE PROJECT KIT", font=font(UB, 21, 700), fill=ACCENT)
d.text((M + 84 * S, 132 * S), "plugin · installer · MIT", font=font(UB, 18, 400), fill=DIM)

# headline
h1 = font(UB, 54, 700)
y = 208 * S
for line in ["Make Claude Code", "know your project."]:
    d.text((M, y), line, font=h1, fill=TEXT)
    y += 64 * S
# subline
sub = font(UB, 23, 400)
y += 18 * S
for line in ["One command detects your stack and writes", "CLAUDE.md, rules, hooks, skills, agents and MCP."]:
    d.text((M, y), line, font=sub, fill=MUTED)
    y += 33 * S

# chips
chip_f = font(UB, 17, 500)
x, cy = M, 522 * S
for label in ["Safety guard", "Done gate", "/pr  /start-issue", "Credit caps"]:
    w = d.textlength(label, font=chip_f) + 30 * S
    d.rounded_rectangle([x, cy, x + w, cy + 38 * S], radius=19 * S, outline=(86, 74, 64), width=2 * S, fill=(32, 28, 25))
    d.text((x + 15 * S, cy + 9 * S), label, font=chip_f, fill=TEXT)
    x += w + 12 * S

# terminal window
tx0, ty0, tx1, ty1 = 740 * S, 112 * S, 1212 * S, 500 * S
d.rounded_rectangle([tx0 + 8 * S, ty0 + 12 * S, tx1 + 8 * S, ty1 + 12 * S], radius=18 * S, fill=(10, 9, 8))  # shadow
d.rounded_rectangle([tx0, ty0, tx1, ty1], radius=18 * S, fill=TERM, outline=(58, 51, 46), width=2 * S)
d.rounded_rectangle([tx0, ty0, tx1, ty0 + 44 * S], radius=18 * S, fill=TERM_BAR)
d.rectangle([tx0, ty0 + 26 * S, tx1, ty0 + 44 * S], fill=TERM_BAR)
for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
    cx = tx0 + (24 + i * 22) * S
    d.ellipse([cx - 7 * S, ty0 + 15 * S, cx + 7 * S, ty0 + 29 * S], fill=c)
d.text((tx0 + 100 * S, ty0 + 12 * S), "claude · my-app (main)", font=font(UB, 16, 400), fill=DIM)

mono = ImageFont.truetype(MONO, 18 * S)
monob = ImageFont.truetype(MONOB, 18 * S)
lines = [
    [(">", ACCENT, monob), (" /cct:setup", TEXT, mono)],
    [("  Found ", MUTED, mono), ("TypeScript, pnpm, Vitest", TEXT, mono)],
    [("  ? ", ACCENT, monob), ("Thorough or quick? ", MUTED, mono), ("Quick", TEXT, mono)],
    [("  ✓ ", GREEN, monob), ("CLAUDE.md · 6 rules · guard", TEXT, mono)],
    [("  ✓ ", GREEN, monob), ("done gate: related tests", TEXT, mono)],
    [("  PASS ", GREEN, monob), ("pnpm vitest related", TEXT, mono)],
    [("", TEXT, mono)],
    [(">", ACCENT, monob), (" /pr", TEXT, mono), ("  → PR #42 opened", MUTED, mono)],
]
ly = ty0 + 64 * S
for parts in lines:
    lx = tx0 + 26 * S
    for txt, col, f in parts:
        d.text((lx, ly), txt, font=f, fill=col)
        lx += d.textlength(txt, font=f)
    ly += 34 * S
# status line inside the window
sb = ty1 - 40 * S
d.rectangle([tx0 + 2 * S, sb, tx1 - 2 * S, sb + 2 * S], fill=(44, 39, 35))
d.text((tx0 + 26 * S, sb + 11 * S), "Opus · my-app (main) · $0.42 · guard standard", font=ImageFont.truetype(MONO, 15 * S), fill=DIM)

# footer
foot = font(UB, 18, 400)
d.text((M, 590 * S), "github.com/John99101/claude-code-project-template", font=foot, fill=DIM)
right = "Linux · macOS · Windows"
d.text((W - M - d.textlength(right, font=foot), 590 * S), right, font=foot, fill=DIM)

img.resize((1280, 640), Image.LANCZOS).save(OUT, optimize=True)
print("saved", OUT)

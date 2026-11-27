#!/usr/bin/env python3
"""Draws .github/demo/demo.gif, the animated terminal session at the top of the README.

The kit's messages in it are real: the script first runs the hooks from hooks/ in a throwaway project and captures
what they print (the setup notice, the dependency block, the test guard, the claim check, the status line). Claude's
own lines in between are illustrative, and the README says so.

Usage:  python3 .github/demo/make_demo.py
Needs Pillow (`pip install pillow`) and the DejaVu Sans Mono font. Maintainer tool only; the kit doesn't use it.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
HOOKS = os.path.join(ROOT, "hooks")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "demo.gif")

W, H = 960, 560
PAD, BAR, STATUS = 22, 36, 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SIZE, LINE = 15, 21
COLS = 98

BG, BAR_BG, BORDER = (18, 16, 15), (40, 36, 32), (62, 55, 49)
TEXT, DIM, MUTED = (236, 230, 222), (126, 117, 108), (180, 170, 160)
ACCENT, GREEN, RED, AMBER, BLUE = (217, 119, 87), (126, 199, 129), (235, 110, 100), (230, 180, 90), (120, 170, 230)


# --- real hook output ------------------------------------------------------------------------------------------

def run_hook(name, payload, env):
    r = subprocess.run([sys.executable, os.path.join(HOOKS, name)], input=json.dumps(payload),
                       capture_output=True, text=True, env=env, timeout=60)
    return r.stdout.strip()


def capture():
    """The hooks' own words for each scene."""
    tmp = tempfile.mkdtemp(prefix="cct-demo-")
    proj = os.path.join(tmp, "my-app")
    os.makedirs(os.path.join(proj, ".claude"))
    env = dict(os.environ, HOME=tmp, USERPROFILE=tmp, CLAUDE_PROJECT_DIR=proj)
    env.pop("CLAUDE_PLUGIN_ROOT", None)

    status_payload = {"model": {"display_name": "Opus"}, "cost": {"total_cost_usd": 0.42},
                      "workspace": {"current_dir": proj, "project_dir": proj}}
    open(os.path.join(proj, ".claude", "cct-pending"), "w").close()
    setup = json.loads(run_hook("session_start.py", {"source": "startup"}, env))["systemMessage"]
    pending = run_hook("statusline.py", dict(status_payload, cost={"total_cost_usd": 0.0}), env)
    os.remove(os.path.join(proj, ".claude", "cct-pending"))

    registry = os.path.join(tmp, "registry")  # an empty local registry: every name is unknown
    os.makedirs(registry)
    env["CCT_REGISTRY_BASE"] = "file:" + urllib.request.pathname2url(registry)
    deps = json.loads(run_hook("deps_guard.py", {"tool_input": {"command": "npm install react-codeshift"}}, env))
    deps = deps["hookSpecificOutput"]["permissionDecisionReason"]

    test = os.path.join(proj, "src", "reports", "export.test.ts")
    os.makedirs(os.path.dirname(test))
    with open(test, "w") as f:
        f.write("it('exports totals', () => {\n")
    guard = json.loads(run_hook("protect_files.py", {"tool_input": {
        "file_path": test, "old_string": "it('exports totals', () => {",
        "new_string": "it.skip('exports totals', () => {"}}, env))["hookSpecificOutput"]["permissionDecisionReason"]

    transcript = os.path.join(tmp, "t.jsonl")
    with open(transcript, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "fix the export"}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Fixed the rounding in export.ts. All tests pass."}]}}) + "\n")
    claim = json.loads(run_hook("claim_check.py", {"transcript_path": transcript}, env))["reason"]

    status = run_hook("statusline.py", status_payload, env)
    return {"setup": setup, "deps": deps, "guard": guard, "claim": claim, "status": status, "pending": pending}


# --- drawing ---------------------------------------------------------------------------------------------------

font = ImageFont.truetype(FONT, SIZE)
bold = ImageFont.truetype(FONT_B, SIZE)
small = ImageFont.truetype(FONT, 13)
ROWS = (H - BAR - STATUS - PAD * 2) // LINE


def wrap(spans, indent=0):
    """Split (text, color, bold) spans into screen lines of at most COLS characters."""
    lines, cur, width = [], [], 0
    pad = [(" " * indent, TEXT, False)] if indent else []
    for text, color, is_bold in spans:
        for i, part in enumerate(text.split("\n")):
            if i:
                lines.append(cur)
                cur, width = list(pad), indent
            while part:
                room = COLS - width
                if len(part) <= room:
                    cur.append((part, color, is_bold))
                    width += len(part)
                    break
                cut = part.rfind(" ", 0, room)
                cut = room if cut <= 0 else cut + 1
                cur.append((part[:cut], color, is_bold))
                lines.append(cur)
                part = part[cut:]
                cur, width = list(pad), indent
    lines.append(cur)
    return lines


class Screen:
    def __init__(self, status):
        self.lines, self.status = [], status
        self.frames, self.durations = [], []

    def frame(self, ms, cursor=False):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, BAR], fill=BAR_BG)
        for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
            cx = 22 + i * 22
            d.ellipse([cx - 7, 11, cx + 7, 25], fill=c)
        d.text((W // 2, BAR // 2), "claude · my-app", font=small, fill=DIM, anchor="mm")
        y, x_end = BAR + PAD, PAD
        for line in self.lines[-ROWS:]:
            x = PAD
            for text, color, is_bold in line:
                f = bold if is_bold else font
                d.text((x, y), text, font=f, fill=color)
                x += d.textlength(text, font=f)
            x_end = x
            y += LINE
        if cursor:
            d.rectangle([x_end + 2, y - LINE + 3, x_end + 10, y - 3], fill=ACCENT)
        d.line([0, H - STATUS, W, H - STATUS], fill=BORDER, width=1)
        d.text((PAD, H - STATUS + 8), self.status, font=small, fill=DIM)
        self.frames.append(img)
        self.durations.append(ms)

    def out(self, spans, indent=0, ms=500):
        self.lines += wrap(spans, indent)
        self.frame(ms)

    def type(self, prompt, text, ms_end=500):
        self.lines.append([(prompt, ACCENT, True)])
        for i in range(0, len(text) + 1, 2):
            self.lines[-1] = [(prompt, ACCENT, True), (text[:i], TEXT, False)]
            self.frame(45, cursor=True)
        self.frame(ms_end)

    def blank(self):
        self.lines.append([])

    def clear(self):
        self.lines = []


def build(words):
    s = Screen(words["pending"])
    s.type("$ ", "claude", 700)
    s.out([(words["setup"], AMBER, False)], indent=6, ms=1600)
    s.blank()
    s.type("> ", "/cct:setup", 600)
    s.out([("● ", ACCENT, False),
           ("Found TypeScript + Fastify, pnpm, Vitest, ESLint, Postgres, Conventional Commits.", TEXT, False)], ms=900)
    for q, a in [("How thorough should setup be?", "Quick"),
                 ("What must pass before I say I'm done?", "lint, typecheck, test"),
                 ("Run them when I finish a turn?", "Yes, only related tests"),
                 ("Does the team also use other AI tools?", "Cursor")]:
        s.out([("  ? ", ACCENT, True), (q.ljust(40), MUTED, False), ("› ", DIM, False), (a, TEXT, False)], ms=550)
    s.status = words["status"]
    s.out([("  ✓ ", GREEN, True), ("CLAUDE.md · AGENTS.md · 6 rules · guard · done gate · .mcp.json", TEXT, False)],
          ms=600)
    s.out([("  PASS ", GREEN, True), ("pnpm lint 2.1 s   ", TEXT, False), ("PASS ", GREEN, True),
           ("pnpm typecheck 4.0 s   ", TEXT, False), ("PASS ", GREEN, True), ("vitest related 1.3 s", TEXT, False)],
          ms=2200)

    s.clear()
    s.type("> ", "add CSV export to the reports page", 600)
    s.out([("● ", ACCENT, False), ("I'll use react-codeshift to build the export.", TEXT, False)], ms=700)
    s.out([("  ● ", BLUE, False), ("Bash", BLUE, True), ("(npm install react-codeshift)", MUTED, False)], ms=700)
    s.out([("  ✗ ", RED, True), (words["deps"], RED, False)], indent=4, ms=2600)
    s.out([("● ", ACCENT, False), ("That package doesn't exist. Using papaparse instead.", TEXT, False)], ms=1200)
    s.blank()
    s.out([("  ● ", BLUE, False), ("Edit", BLUE, True), ("(src/reports/export.test.ts)  ", MUTED, False),
           ("it( ", DIM, False), ("→ it.skip(", RED, False)], ms=700)
    s.out([("  ? ", AMBER, True), (words["guard"], AMBER, False)], indent=4, ms=2400)
    s.out([("    Allow? › ", DIM, False), ("No", TEXT, True)], ms=1200)

    s.clear()
    s.out([("● ", ACCENT, False), ("Fixed the rounding in export.ts. All tests pass.", TEXT, False)], ms=1200)
    s.out([("  ↩ ", AMBER, True), (words["claim"], AMBER, False)], indent=4, ms=2800)
    s.out([("  ● ", BLUE, False), ("Bash", BLUE, True),
           ("(pnpm vitest related --run src/reports/export.ts)", MUTED, False)], ms=900)
    s.out([("  ✓ ", GREEN, True), ("12 passed", GREEN, False)], ms=800)
    s.out([("● ", ACCENT, False), ("Verified: 12 tests pass, including the new export test.", TEXT, False)], ms=1800)

    s.clear()
    for _ in range(5):
        s.blank()
    s.out([("  Claude Code Project Kit", ACCENT, True)], ms=10)
    s.out([("  One command sets up Claude Code for your project, then keeps it honest.", TEXT, False)], ms=10)
    s.blank()
    s.out([("  /plugin install cct --marketplace John99101/claude-code-project-template", GREEN, False)], ms=10)
    s.out([("  /cct:setup", GREEN, False)], ms=4000)
    return s


def save(screen):
    # one shared palette keeps every frame's colours identical and the file small
    sample = Image.new("RGB", (W, H * 3))
    for i, f in enumerate((screen.frames[len(screen.frames) // 3], screen.frames[2 * len(screen.frames) // 3],
                           screen.frames[-1])):
        sample.paste(f, (0, H * i))
    palette = sample.quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in screen.frames]
    frames[0].save(OUT, save_all=True, append_images=frames[1:], duration=screen.durations, loop=0, optimize=True)
    print(f"saved {OUT}: {len(frames)} frames, {sum(screen.durations) / 1000:.1f} s, "
          f"{os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    save(build(capture()))

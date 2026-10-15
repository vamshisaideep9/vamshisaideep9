#!/usr/bin/env python3
"""Builds the animated SVG assets for the profile README from profile.config.json (+ stats.json).

Style: hacker terminal — black CRT screens, phosphor-green and amber JetBrains Mono, scanlines, glow,
flicker, Matrix rain, ASCII art and console output (boot log, systemctl, neofetch, stats bars).

Usage:  pip install fonttools brotli pyfiglet && python scripts/build_assets.py
Fonts are subset per SVG and embedded as base64 woff2, so they render inside GitHub's <img> sandbox
(GitHub strips external resources and scripts, but keeps CSS + SMIL animation).
"""
import base64, io, json, os, random, textwrap
from datetime import date, timedelta
from xml.sax.saxutils import escape
import pyfiglet
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")
CFG = json.load(open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8"))
_SP = os.path.join(ROOT, "stats.json")
STATS = json.load(open(_SP, encoding="utf-8")) if os.path.exists(_SP) else None
USER = CFG["username"]

# ── design tokens ─────────────────────────────────────────────────────────
BG, PANEL, BAR, LINE = "#030703", "#060d07", "#0b160d", "#163a20"
GREEN, GREEN_HI, GREEN_DIM, GREEN_LO = "#39ff7a", "#b6ffc9", "#1f9e4a", "#0f3d1d"
AMBER, CYAN, RED, MAGENTA = "#ffb347", "#4df3ff", "#ff5f56", "#ff2a6d"
TEXT = "#c8ffd4"
W = 1200
FS = 14                 # body font size; JetBrains Mono advance = 0.6em
CW = FS * 0.6           # one terminal column in px
LH = 22                 # line height

FONT_FILES = {"JB": "JetBrainsMono-Regular.woff2", "JBB": "JetBrainsMono-Bold.woff2", "VT": "vt323-latin-400-normal.woff2"}


def fonts_css(spec):
    """spec: {"JB"|"JBB"|"VT": text_used} → @font-face rules with per-SVG subsets."""
    css = []
    for fam, text in spec.items():
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = []
        f = TTFont(os.path.join(FONTS, FONT_FILES[fam]))
        s = subset.Subsetter(opts); s.populate(text=text + " 0123456789█▌_>$~/"); s.subset(f)
        buf = io.BytesIO(); f.flavor = "woff2"; f.save(buf)
        css.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}")
    return "".join(css)


DEFS = f"""
<filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="2.2" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="bloom" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5" result="b"/>
  <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" opacity=".35"/></pattern>
<radialGradient id="vignette" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".75"/></radialGradient>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GREEN}" stop-opacity="0"/><stop offset=".5" stop-color="{GREEN}" stop-opacity=".07"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></linearGradient>
"""

BASE_CSS = f"""
.t{{font:400 {FS}px 'JB',monospace;fill:{TEXT};white-space:pre}} .b{{font-family:'JBB','JB',monospace;font-weight:700}}
.g{{fill:{GREEN}}} .gh{{fill:{GREEN_HI}}} .gd{{fill:{GREEN_DIM}}} .a{{fill:{AMBER}}} .c{{fill:{CYAN}}} .r{{fill:{RED}}} .m{{fill:{MAGENTA}}}
.flicker{{animation:flicker 7s infinite steps(1)}}
@keyframes flicker{{0%,100%{{opacity:1}}41%{{opacity:.93}}42%{{opacity:1}}77%{{opacity:.96}}78%{{opacity:1}}}}
.blink{{animation:blink 1s steps(1) infinite}} @keyframes blink{{50%{{opacity:0}}}}
@keyframes type{{from{{clip-path:inset(0 100% 0 0)}}to{{clip-path:inset(0 0 0 0)}}}}
@keyframes show{{from{{opacity:0}}to{{opacity:1}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none!important}}}}
"""


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  ✓ assets/{name}  ({len(content)//1024} KB)")


def svg(w, h, body, css, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title><style>{css}{BASE_CSS}</style><defs>{DEFS}</defs>{body}</svg>")


def window(w, h, path, body, r=12, rain=False, beam=True):
    """A CRT terminal window: title bar, phosphor content, scanlines, rolling beam and vignette."""
    clip = "cw"
    beam_svg = (f'<rect x="0" y="-120" width="{w}" height="120" fill="url(#beam)">'
                f'<animate attributeName="y" values="-120;{h}" dur="7s" repeatCount="indefinite"/></rect>') if beam else ""
    return f"""
    <defs><clipPath id="{clip}"><rect width="{w}" height="{h}" rx="{r}"/></clipPath></defs>
    <g clip-path="url(#{clip})">
      <rect width="{w}" height="{h}" fill="{BG}"/>
      {rain_svg(w, h) if rain else ''}
      <rect width="{w}" height="34" fill="{BAR}"/><rect y="33.5" width="{w}" height="1" fill="{LINE}"/>
      <circle cx="20" cy="17" r="5.5" fill="none" stroke="{RED}" stroke-opacity=".8"/><circle cx="38" cy="17" r="5.5" fill="none" stroke="{AMBER}" stroke-opacity=".8"/>
      <circle cx="56" cy="17" r="5.5" fill="{GREEN}"><animate attributeName="opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/></circle>
      <text class="t gd" x="{w/2}" y="21.5" text-anchor="middle" style="font-size:12px">{escape(path)}</text>
      <text class="t gd" x="{w - 16}" y="21.5" text-anchor="end" style="font-size:12px">⏻ tty1</text>
      <g class="flicker" filter="url(#glow)">{body}</g>
      {beam_svg}
      <rect width="{w}" height="{h}" fill="url(#scan)" pointer-events="none"/>
      <rect width="{w}" height="{h}" fill="url(#vignette)" pointer-events="none"/>
    </g>
    <rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="{LINE}"/>
    <rect x="1.5" y="1.5" width="{w-3}" height="{h-3}" rx="{r-1}" fill="none" stroke="{GREEN}" stroke-opacity=".08"/>"""


RAIN_CHARS = "01<>/{}[]$#*+=ABCDEF0123456789"


def rain_svg(w, h, seed=3, step=24, size=14):
    """Matrix-style digital rain: columns of glyphs falling at different speeds."""
    rnd = random.Random(seed)
    cols, n = [], int(h / (size + 4)) + 2
    for x in range(8, w, step):
        chars = [rnd.choice(RAIN_CHARS) for _ in range(n)]
        tsp = "".join(f'<tspan x="{x}" dy="{size + 4}"' + (' class="gh"' if j == n - 1 else "") + f">{escape(c)}</tspan>" for j, c in enumerate(chars))
        dur = rnd.uniform(5, 13)
        cols.append(f'<text class="t rain" style="font-size:{size}px;animation-duration:{dur:.1f}s;animation-delay:-{rnd.uniform(0, dur):.1f}s" y="{-h}">{tsp}</text>')
    return (f'<g opacity=".16">{"".join(cols)}</g>'
            f'<style>.rain{{fill:{GREEN};animation:fall linear infinite}} @keyframes fall{{from{{transform:translateY(0)}}to{{transform:translateY({2*h}px)}}}}</style>')


def line(x, y, segs, cls="", anchor=None):
    """segs: [(text, class)] → one terminal line."""
    inner = "".join(f'<tspan class="{c}">{escape(t)}</tspan>' if c else escape(t) for t, c in segs)
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text class="t {cls}" x="{x:.1f}" y="{y}"{a}>{inner}</text>'


def seg_text(segs):
    return "".join(t for t, _ in segs)


def typed(x, y, segs, delay, cps=40, cls=""):
    """A line that types itself out after `delay` seconds."""
    n = max(len(seg_text(segs)), 1)
    return (f'<g style="animation:type {n/cps:.2f}s steps({n}) {delay:.2f}s both">{line(x, y, segs, cls)}</g>', delay + n / cps)


def appear(x, y, segs, delay, cls=""):
    return f'<g style="animation:show .15s {delay:.2f}s both">{line(x, y, segs, cls)}</g>'


# ── 1. HEADER: boot log → glitching ASCII name → rotating roles ────────────
def header():
    H = 560
    first, last = CFG["name"].split(" ", 1)
    art1 = pyfiglet.figlet_format(first.upper(), font="ansi_shadow").rstrip("\n").split("\n")
    art2 = pyfiglet.figlet_format(last.upper(), font="ansi_shadow").rstrip("\n").split("\n")
    boot = list(CFG["boot"])
    if STATS:
        boot[-1] = f"{boot[-1]}: {STATS['repos']} repos ({STATS['private_repos']} private)"
    parts, t = [], .3
    x0, y = 32, 66
    for b in boot:
        dots = "." * max(3, 50 - len(b))
        parts.append(appear(x0, y, [("[  ", "gd"), ("OK", "g b"), ("  ] ", "gd"), (b + " ", ""), (dots, "gd")], t))
        t += .28; y += LH - 2
    art_size = 13; art_lh = art_size * 1.32   # JetBrains Mono cell height, so box glyphs join
    ay = y + 26

    def art_block(lines, y0, cls):
        return "".join(f'<text class="t {cls}" x="{x0}" y="{y0 + i*art_lh:.1f}" style="font-size:{art_size}px">{escape(l)}</text>' for i, l in enumerate(lines))
    y2 = ay + len(art1) * art_lh + 4
    a = art_block(art1, ay, "g") + art_block(art2, y2, "g")
    glitch = (f'<g class="gl1">{art_block(art1, ay, "m")}{art_block(art2, y2, "m")}</g>'
              f'<g class="gl2">{art_block(art1, ay, "c")}{art_block(art2, y2, "c")}</g>')
    art_end = y2 + len(art2) * art_lh
    name_svg = f'<g style="animation:show .6s {t + .2:.2f}s both">{glitch}{a}</g>'

    # Rotating roles: typed in, held, erased.
    roles = CFG["roles"]; n = len(roles); step = 4.2; cyc = n * step; on = 100 / n
    ry = art_end + 36
    role_css = "".join(f".ro{i}{{clip-path:inset(0 100% 0 0);animation:ro {cyc:.1f}s steps(30) infinite {t + 1.2 + i*step - cyc:.1f}s}}" for i in range(n))
    role_css += (f"@keyframes ro{{0%{{clip-path:inset(0 100% 0 0)}}{on*.32:.2f}%{{clip-path:inset(0 0 0 0)}}{on*.8:.2f}%{{clip-path:inset(0 0 0 0)}}"
                 f"{on*.97:.2f}%{{clip-path:inset(0 100% 0 0)}}100%{{clip-path:inset(0 100% 0 0)}}}}")
    prompt = [(f"{USER}@ai", "g b"), (":", "gd"), ("~", "c"), ("$ ", "gd"), ("echo $ROLE", "")]
    roles_svg = (line(x0, ry, prompt) +
                 "".join(f'<g class="ro{i}">{line(x0, ry + LH, [("> ", "a"), (r, "gh")])}</g>' for i, r in enumerate(roles)))

    # System panel (right): box-drawn with live numbers.
    px, pw = 744, 424
    cols = int(pw / CW)
    rows = [("user", CFG["name"]), ("role", CFG["title"]), ("status", "● ONLINE · open to work"), ("mode", "full-time · freelance")]
    if STATS:
        rows += [("contrib", f"{STATS['year_contributions']:,} / 12 months"), ("commits", f"{STATS['commits']:,}"),
                 ("prs", f"{STATS['prs_merged']:,} merged"), ("streak", f"{STATS['streak_longest']} days max")]
    head = "[ SYSTEM ]"
    bh = (len(rows) + 1) * LH + 6
    box = [f'<rect x="{px}" y="64" width="{pw}" height="{bh}" rx="6" fill="{GREEN}" fill-opacity=".03" stroke="{GREEN_DIM}"/>'
           f'<rect x="{px + 14}" y="56" width="{(len(head) + 2) * CW:.0f}" height="16" fill="{BG}"/>{line(px + 14 + CW, 69, [(head, "g b")])}']
    for i, (k, v) in enumerate(rows):
        vcls = "g b" if k == "status" else "a" if k in ("contrib", "commits", "prs", "streak") else "gh"
        box.append(appear(px + 16, 70 + (i + 1) * LH, [(f"{k:<9}", "gd"), (v, vcls)], .4 + i * .12))
    my = 70 + (len(rows) + 2) * LH + 16
    meters = []
    bw = pw - 120
    for i, (k, pct) in enumerate([("AI", 92), ("WEB", 86), ("MOBILE", 74), ("SEO", 80)]):
        yy = my + i * (LH - 2)
        full = (bw - 4) * pct / 100
        meters.append(f'{line(px, yy, [(f"{k:<7}", "gd")])}'
                      f'<rect x="{px + 70}" y="{yy - 11}" width="{bw}" height="12" fill="none" stroke="{GREEN_LO}"/>'
                      f'<rect x="{px + 72}" y="{yy - 9}" width="{full:.0f}" height="8" fill="{GREEN}" opacity=".85">'
                      f'<animate attributeName="width" values="0;{full:.0f};{full*.88:.0f};{full:.0f}" keyTimes="0;.25;.6;1" dur="{4 + i*.7:.1f}s" repeatCount="indefinite"/></rect>'
                      f'{line(px + 80 + bw, yy, [(f"{pct}%", "a")])}')
    panel = f'<g style="animation:show .5s .3s both">{"".join(box)}{"".join(meters)}</g>'

    alltxt = "".join(art1 + art2) + "".join(boot) + "[] .:" + "".join(roles) + seg_text(prompt) + head + "".join(k + v for k, v in rows) + "AIWEBMOBILESEO%"
    css = fonts_css({"JB": alltxt + RAIN_CHARS, "JBB": "OK" + USER + "@ai● ONLINE · open to work[ SYSTEM ]"}) + f"""
    .gl1,.gl2{{opacity:0}} .gl1{{animation:g1 5s infinite steps(1)}} .gl2{{animation:g2 5s infinite steps(1)}}
    @keyframes g1{{0%,88%,100%{{opacity:0;transform:none}}89%{{opacity:.75;transform:translate(-4px,1px)}}91%{{opacity:.75;transform:translate(3px,-1px)}}93%{{opacity:0}}96%{{opacity:.6;transform:translate(-2px,0)}}97%{{opacity:0}}}}
    @keyframes g2{{0%,88%,100%{{opacity:0;transform:none}}89%{{opacity:.75;transform:translate(4px,-1px)}}91%{{opacity:.75;transform:translate(-3px,1px)}}93%{{opacity:0}}96%{{opacity:.6;transform:translate(2px,0)}}97%{{opacity:0}}}}
    {role_css}
    @media (prefers-reduced-motion: reduce){{.ro0{{clip-path:none!important}}}}"""
    body = "".join(parts) + name_svg + f'<g style="animation:show .3s {t + 1:.2f}s both">{roles_svg}</g>' + panel
    write("header.svg", svg(W, H, window(W, H, f"{USER}@ai: ~ — boot", body, rain=True), css, f"{CFG['name']} — {CFG['title']}"))


# ── 2. SECTION PROMPTS (Kali-style two-line prompt, command types itself) ──
SECTIONS = [("about", "about", "cat about.md"), ("services", "services", "systemctl list-units --type=service --state=running"),
            ("projects", "projects", "ls -la ~/projects --featured"), ("stack", "stack", "neofetch"),
            ("stats", "stats", "./stats --include-private --since 2024"), ("feed", "feed", "tail -f ~/feed.log"),
            ("guestbook", "guestbook", "cat /var/log/visitors.log"), ("contact", "contact", "./contact.sh --secure")]


def section(slug, path, cmd):
    H = 74
    l1 = [("┌──(", "gd"), (f"{USER}㉿ai", "g b"), (")-[", "gd"), (f"~/{path}", "c b"), ("]", "gd")]
    l2p = [("└─", "gd"), ("$ ", "a b")]
    n = len(cmd)
    css = fonts_css({"JB": seg_text(l1) + seg_text(l2p) + cmd, "JBB": f"{USER}㉿ai~/{path}$ "})
    cx = 24 + len(seg_text(l2p)) * CW
    body = f"""<rect width="{W}" height="{H}" rx="10" fill="{BG}"/><rect width="{W}" height="{H}" rx="10" fill="url(#scan)"/>
    <rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="10" fill="none" stroke="{LINE}"/>
    <g filter="url(#glow)">{line(24, 30, l1)}{line(24, 54, l2p)}
      <g style="animation:type {n*.045:.2f}s steps({n}) .3s both">{line(cx, 54, [(cmd, "gh")])}</g>
      <rect class="blink" x="{cx + n*CW + 3:.1f}" y="41" width="{CW:.1f}" height="17" fill="{GREEN}"/></g>"""
    write(f"section-{slug}.svg", svg(W, H, body, css, f"$ {cmd}"))


# ── 3. ABOUT TERMINAL ─────────────────────────────────────────────────────
def terminal():
    blocks = [b for b in CFG["terminal"] if b["cmd"] != "status"]
    status = next((b for b in CFG["terminal"] if b["cmd"] == "status"), None)
    if STATS:
        langs = " · ".join(f"{l['name']} {round(l['pct'])}%" for l in STATS["languages"][:3])
        blocks.append({"cmd": "gh stats --include-private", "out": [
            f"activity:  {STATS['year_contributions']:,} contributions in the last 12 months",
            f"repos:     {STATS['repos']} ({STATS['private_repos']} private) · {STATS['prs_merged']:,} PRs merged",
            f"langs:     {langs}"]})
    if status:
        blocks.append(status)
    rows = []
    for b in blocks:
        rows.append(("cmd", b["cmd"])); rows += [("out", o) for o in b["out"]]
    top = 64
    H = top + LH * (len(rows) + 1) + 26
    t, items, x = .3, [], 28
    prompt = [(f"{USER}@ai", "g b"), (":", "gd"), ("~", "c"), ("$ ", "gd")]
    px = x + len(seg_text(prompt)) * CW
    for i, (kind, txt) in enumerate(rows):
        y = top + i * LH
        if kind == "cmd":
            items.append(appear(x, y, prompt, t))
            g, t = typed(px, y, [(txt, "gh")], t + .1, cps=34)
            items.append(g); t += .2
        else:
            if txt.startswith("●"):
                segs = [(txt, "g b")]
            elif txt.startswith("⎇"):
                segs = [(txt, "a")]
            elif ":" in txt and not txt.startswith(CFG["name"].split()[0]):
                k, v = txt.split(":", 1); segs = [(k + ":", "c"), (v, "")]
            else:
                segs = [(txt, "gh")]
            items.append(appear(x, y, segs, t)); t += .12
    ye = top + len(rows) * LH
    items.append(f'<g style="animation:show .1s {t:.2f}s both">{line(x, ye, prompt)}<rect class="blink" x="{px + 2:.1f}" y="{ye - 14}" width="{CW:.1f}" height="18" fill="{GREEN}"/></g>')
    alltxt = "".join(r[1] for r in rows) + seg_text(prompt)
    css = fonts_css({"JB": alltxt, "JBB": alltxt})
    write("terminal.svg", svg(W, H, window(W, H, f"{USER}@ai: ~ — zsh", "".join(items)), css, "whoami — terminal intro"))


# ── 4. SERVICES as systemd units ──────────────────────────────────────────
def services():
    svc = CFG["services"]
    cols, top, bh = 2, 66, 138
    rows_n = -(-len(svc) // cols)
    H = top + rows_n * bh + 4
    colw = (W - 56) / cols
    out, alltxt = [], ""
    for i, s in enumerate(svc):
        x = 28 + (i % cols) * colw
        y = top + (i // cols) * bh
        words = [w for w in s["title"].lower().replace("&", "").replace("-", " ").split() if w not in ("apps", "and")]
        unit = "-".join(words[:2]) + ".service"
        lines = [
            [("● ", "g b dot"), (unit, "gh b"), (" — ", "gd"), (s["title"], "a")],
            [("   Loaded: ", "gd"), (f"loaded (/etc/systemd/{unit}; ", ""), ("enabled", "g"), (")", "")],
            [("   Active: ", "gd"), ("active (running)", "g b"), (" since 2024", "gd")],
        ] + [[("   ├─ " if j < len(s["points"]) - 1 else "   └─ ", "gd"), (p, "")] for j, p in enumerate(s["points"])]
        for j, l in enumerate(lines):
            alltxt += seg_text(l)
            out.append(appear(x, y + j * (LH - 2), l, .2 + i * .25 + j * .06))
    css = fonts_css({"JB": alltxt, "JBB": alltxt}) + ".dot{animation:blink 1.6s steps(1) infinite}"
    write("services.svg", svg(W, H, window(W, H, "systemctl — services", "".join(out)), css, "Services: " + ", ".join(s["title"] for s in svc)))


# ── 5. PROJECT WINDOWS ────────────────────────────────────────────────────
def project(p, idx):
    PW, PH = 590, 320
    x = 22
    cols = int((PW - 2 * x) / CW)
    desc = textwrap.wrap(p["desc"], cols - 1)[:4]
    tags = " ".join(f"[{t}]" for t in p["tags"][:4])
    perms = "drwxr-xr-x" if idx % 2 == 0 else "drwxr-x---"
    hdr = [
        [(perms, "gd"), ("  ", ""), (p["metric"], "a"), ("  ", ""), (p["slug"] + "/", "g b")],
        [("$ ", "a b"), ("cat README.md", "gh")],
        [("# ", "gd"), (p["title"], "g b")],
        [("> ", "gd"), (p["role"], "c")],
    ]
    items, y = [], 64
    for j, segs in enumerate(hdr):
        items.append(appear(x, y, segs, .2 + j * .15)); y += LH + (6 if j == 1 else 0)
    y += 6
    for j, d in enumerate(desc):
        items.append(appear(x, y, [(d, "")], .9 + j * .08)); y += LH - 2
    alltxt = "".join(seg_text(s) for s in hdr) + "".join(desc) + tags + p["label"].upper() + "[ OPEN ↗ ]"
    items.append(appear(x, PH - 34, [(tags, "gd")], 1.4))
    bx = PW - 22 - 10 * CW
    items.append(f'<g style="animation:show .2s 1.6s both"><rect x="{bx - 8:.0f}" y="{PH - 53}" width="{10*CW + 16:.0f}" height="28" fill="{GREEN}" opacity=".12" stroke="{GREEN}">'
                 f'<animate attributeName="opacity" values=".1;.35;.1" dur="2s" repeatCount="indefinite"/></rect>{line(bx, PH - 34, [("[ OPEN ↗ ]", "g b")])}</g>')
    items.append(line(PW - 22, 64, [(p["label"].upper(), "a")], anchor="end"))
    css = fonts_css({"JB": alltxt, "JBB": alltxt})
    write(f"project-{p['slug']}.svg", svg(PW, PH, window(PW, PH, f"~/projects/{p['slug']}", "".join(items), beam=False), css, f"{p['title']} — {p['desc']}"))


# ── 6. NEOFETCH STACK ─────────────────────────────────────────────────────
def stack():
    logo = pyfiglet.figlet_format("VSD", font="ansi_shadow").rstrip("\n").split("\n")
    info = [[(f"{USER}", "g b"), ("@", "gd"), ("ai", "g b")], [("─" * (len(USER) + 3), "gd")]]
    rows = list(CFG["neofetch"])
    if STATS:
        rows.insert(3, ["Uptime", f"since {STATS['since']} · {STATS['streak_longest']}-day best streak"])
        rows.append(["Languages", " · ".join(f"{l['name']} {round(l['pct'])}%" for l in STATS["languages"][:4])])
    for k, v in rows:
        info.append([(f"{k}", "a b"), (": ", "gd"), (v, "")])
    lx, ix, top = 40, 40 + 34 * CW, 70
    H = top + max(len(logo) * 21 + 40, len(info) * LH + 40) + 30
    grad = [GREEN_HI, GREEN, GREEN, GREEN_DIM, GREEN_DIM, GREEN_LO]
    logo_svg = "".join(f'<text class="t b" x="{lx}" y="{top + 40 + i*21.1:.1f}" style="font-size:16px;fill:{grad[i % len(grad)]}">{escape(r)}</text>' for i, r in enumerate(logo))
    lines = [appear(ix, top + i * LH, s, .2 + i * .09) for i, s in enumerate(info)]
    by = top + len(info) * LH + 2
    palette = [BG, RED, GREEN, AMBER, "#3b82f6", MAGENTA, CYAN, TEXT]
    blocks = "".join(f'<rect x="{ix + i*30:.0f}" y="{by}" width="30" height="14" fill="{c}"/>' for i, c in enumerate(palette))
    blocks += "".join(f'<rect x="{ix + i*30:.0f}" y="{by + 14}" width="30" height="14" fill="{c}" opacity=".55"/>' for i, c in enumerate(palette))
    alltxt = "".join(logo) + "".join(seg_text(s) for s in info)
    css = fonts_css({"JB": alltxt, "JBB": alltxt})
    body = f'<g style="animation:show .6s both">{logo_svg}</g>{"".join(lines)}<g style="animation:show .3s {.3 + len(info)*.09:.2f}s both">{blocks}</g>'
    write("stack.svg", svg(W, H, window(W, H, "neofetch", body), css, "Tech stack: " + "; ".join(f"{k}: {v}" for k, v in rows)))


# ── 7. STATS: XP bars, ASCII heatmap, language bars, sparkline ────────────
def stats():
    if not STATS:
        return
    st = STATS
    x, top = 28, 66
    bars = [("contributions", st["year_contributions"], 2000, "last 12 months"), ("commits", st["commits"], 2000, f"since {st['since']}"),
            ("prs merged", st["prs_merged"], 500, "all repositories"), ("repositories", st["repos"], 150, f"{st['private_repos']} private"),
            ("longest streak", st["streak_longest"], 60, f"current {st['streak_current']}d")]
    nb, inner = 40, 132
    items, alltxt = [], ""
    hdr_l = f"╭─[ ACTIVITY ]─ public + private + org ─ updated {st['updated']} "
    hdr = [("╭─[ ", "gd"), ("ACTIVITY", "g b"), (" ]─ ", "gd"), ("public + private + org", "a"), (f" ─ updated {st['updated']} ", "gd"), ("─" * (inner - len(hdr_l) + 1) + "╮", "gd")]
    items.append(line(x, top, hdr)); alltxt += seg_text(hdr)
    for i, (k, v, goal, sub) in enumerate(bars):
        y = top + (i + 1) * LH + 6
        filled = min(nb, round(nb * v / goal))
        val = f"{v:,}" + ("d" if k == "longest streak" else "")
        segs = [("│ ", "gd"), (f"{k:<16}", "c"), ("[", "gd"), ("█" * filled, "g"), ("░" * (nb - filled), "gd"), ("] ", "gd"), (f"{val:>6}", "a b"), (f"  {sub}", "gd")]
        items.append(f'<g style="animation:type .9s steps({len(seg_text(segs))}) {.3 + i*.25:.2f}s both">{line(x, y, segs)}</g>')
        alltxt += seg_text(segs)
    # ASCII heatmap of the last year (public + private)
    hy = top + (len(bars) + 2) * LH + 14
    cal = st["calendar"]; weeks = -(-len(cal) // 7)
    nz = sorted(c for c in cal if c)
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]
    glyph = ["·", "░", "▒", "▓", "█"]
    shade = [GREEN_LO, "#14592c", GREEN_DIM, GREEN, GREEN_HI]
    hx = x + 6 * CW
    cw2 = (W - hx - 40) / weeks
    start = date.fromisoformat(st["calendar_start"])
    mon, last = [], None
    for wk in range(weeks):
        d = start + timedelta(days=wk * 7)
        if d.month != last and wk < weeks - 2:
            mon.append(f'<text class="t gd" x="{hx + wk*cw2:.0f}" y="{hy}" style="font-size:11px">{d.strftime("%b")}</text>'); last = d.month
    heat = []
    for wk in range(weeks):
        col = []
        for dy in range(7):
            i = wk * 7 + dy
            if i >= len(cal):
                break
            c = cal[i]; lv = 0 if c == 0 else 1 + sum(c > t for t in q)
            col.append(f'<rect x="{hx + wk*cw2:.1f}" y="{hy + 8 + dy*17}" width="{cw2 - 4:.1f}" height="13" fill="{shade[lv]}"' + (' opacity=".5"' if lv == 0 else "") + "/>")
        heat.append(f'<g style="animation:show .2s {.8 + wk*.025:.3f}s both">{"".join(col)}</g>')
    days = "".join(f'<text class="t gd" x="{x}" y="{hy + 20 + d*17}" style="font-size:11px">{n}</text>' for d, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))
    ly = hy + 20 + 7 * 17 + 12
    leg = [("less", "gd"), (" " * 15, ""), ("more", "gd"), (f"     best day {st['best_day']} · {st['contributions']:,} contributions all-time", "gd")]
    legend = line(x, ly, leg) + "".join(f'<rect x="{x + (5 + i*2.3) * CW:.1f}" y="{ly - 11}" width="12" height="12" fill="{c}"/>' for i, c in enumerate(shade))
    alltxt += "MonWedFriJanFebMarAprMayJunJulAugSepOctNovDec" + seg_text(leg)
    # Languages
    ly2 = ly + LH + 18
    lang_items = []
    for i, l in enumerate([l for l in st["languages"] if l["pct"] >= .5][:5]):
        filled = max(1, round(60 * l["pct"] / 100))
        segs = [("│ ", "gd"), (f"{l['name']:<16}", "c"), ("█" * filled, "a" if i == 0 else "g"), ("░" * (60 - filled), "gd"), (f" {l['pct']:>5.1f}%", "a b")]
        lang_items.append(f'<g style="animation:type .8s steps({len(seg_text(segs))}) {2 + i*.2:.2f}s both">{line(x, ly2 + i*LH, segs)}</g>')
        alltxt += seg_text(segs)
    nl = len(lang_items)
    # Sparkline of weekly totals
    wk_tot = [sum(cal[i:i + 7]) for i in range(0, len(cal), 7)]
    mx = max(wk_tot) or 1
    spark = "".join("▁▂▃▄▅▆▇█"[min(7, int(v / mx * 7.999))] if v else " " for v in wk_tot)
    sy = ly2 + nl * LH + 8
    sp = [("│ ", "gd"), (f"{'weekly trend':<16}", "c"), (spark, "g"), (f"  peak {mx}/wk", "a")]
    alltxt += seg_text(sp)
    end = line(x, sy + LH, [("╰" + "─" * inner + "╯", "gd")])
    H = sy + LH + 30
    lvcss = "".join(f".lv{i}{{fill:{c}}}" for i, c in enumerate(shade))
    body = ("".join(items) + "".join(mon) + days + "".join(heat) + f'<g style="animation:show .3s 1.8s both">{legend}</g>' + "".join(lang_items) +
            f'<g style="animation:type 1.2s steps({len(seg_text(sp))}) 3s both">{line(x, sy, sp)}</g>' + end)
    css = fonts_css({"JB": alltxt + "╰─│╮", "JBB": alltxt}) + lvcss
    write("stats.svg", svg(W, H, window(W, H, "./stats --include-private", body), css,
                           f"GitHub activity incl. private repos: {st['year_contributions']:,} contributions in 12 months, {st['commits']:,} commits, "
                           f"{st['prs_merged']} PRs merged, {st['repos']} repositories ({st['private_repos']} private)"))


# ── 8. ACHIEVEMENTS as an unlock log ──────────────────────────────────────
def achievements():
    if not STATS:
        return
    st = STATS

    def tier(v, s_, a_, b_):
        return "S" if v >= s_ else "A" if v >= a_ else "B" if v >= b_ else "C"
    nlang = len([l for l in st["languages"] if l["pct"] >= .5])
    items = [("COMMITTER", f"{st['commits']:,} commits", tier(st["commits"], 2000, 1000, 300)),
             ("SHIPPER", f"{st['prs_merged']:,} PRs merged", tier(st["prs_merged"], 500, 200, 50)),
             ("BUILDER", f"{st['repos']} repositories", tier(st["repos"], 100, 50, 20)),
             ("UNDER NDA", f"{st['private_repos']} private repos", tier(st["private_repos"], 30, 15, 5)),
             ("MARATHON", f"{st['streak_longest']}-day streak", tier(st["streak_longest"], 60, 30, 14)),
             ("POLYGLOT", f"{nlang} languages", tier(nlang, 6, 4, 3))]
    tcol = {"S": AMBER, "A": GREEN, "B": CYAN, "C": TEXT}
    top, x = 66, 28
    H = top + len(items) * (LH + 6) + 14
    out, alltxt = [], ""
    for i, (k, d, t) in enumerate(items):
        y = top + i * (LH + 6)
        segs = [(f"[{st['updated']} 00:0{i}:00] ", "gd"), ("✓ ACHIEVEMENT UNLOCKED ", "g b"), ("▸ ", "gd"), (f"{k:<11}", "gh b"), (f"{d:<24}", ""), ("tier ", "gd")]
        alltxt += seg_text(segs) + "SABC[]"
        tx = x + len(seg_text(segs)) * CW
        c = tcol[t]
        out.append(f'<g style="animation:show .2s {.3 + i*.35:.2f}s both">{line(x, y, segs)}'
                   f'<rect x="{tx - 4:.0f}" y="{y - 15}" width="{CW*3 + 8:.0f}" height="21" fill="{c}" opacity=".15" stroke="{c}"><animate attributeName="opacity" values=".1;.35;.1" dur="2s" begin="{i*.3:.1f}s" repeatCount="indefinite"/></rect>'
                   f'<text class="t b" x="{tx:.0f}" y="{y}" style="fill:{c}">[{t}]</text></g>')
    css = fonts_css({"JB": alltxt, "JBB": alltxt})
    write("achievements.svg", svg(W, H, window(W, H, "tail /var/log/achievements.log", "".join(out)), css,
                                  "Achievements: " + ", ".join(f"{k} ({d}, tier {t})" for k, d, t in items)))


# ── 9. WEEKLY BAR CHART ───────────────────────────────────────────────────
def activity():
    if not STATS:
        return
    cal = STATS["calendar"]
    wk = [sum(cal[i:i + 7]) for i in range(0, len(cal), 7)]
    mx = max(wk) or 1
    rows, x, top = 12, 28, 70
    bw = (W - 2 * x - 60) / len(wk)
    H = top + rows * 16 + 64
    out = []
    for r in range(0, rows + 1, 3):
        v = round(mx * (rows - r) / rows)
        out.append(f'<text class="t gd" x="{x + 40}" y="{top + r*16 + 4}" text-anchor="end" style="font-size:11px">{v}</text>'
                   f'<line x1="{x + 50}" y1="{top + r*16}" x2="{W - x}" y2="{top + r*16}" stroke="{GREEN_LO}" stroke-dasharray="2 6"/>')
    for i, v in enumerate(wk):
        h = v / mx * rows * 16
        bx = x + 60 + i * bw
        c = GREEN_HI if v == mx else GREEN if v > mx * .5 else GREEN_DIM
        out.append(f'<rect x="{bx:.1f}" y="{top + rows*16 - h:.1f}" width="{bw - 4:.1f}" height="{h:.1f}" fill="{c}" opacity=".9" '
                   f'style="transform-box:fill-box;transform-origin:bottom;animation:grow .6s cubic-bezier(.2,.7,.2,1) {.2 + i*.03:.2f}s both"/>')
    label = f"weekly contributions · last 12 months · public + private · peak {mx}/wk"
    out.append(line(x + 60, top + rows * 16 + 30, [(label, "gd")]))
    css = fonts_css({"JB": label}) + "@keyframes grow{from{transform:scaleY(0)}to{transform:none}}"
    write("activity.svg", svg(W, H, window(W, H, "plot --weekly", "".join(out)), css, f"Weekly contributions over the last 12 months, peak {mx} per week"))


# ── 10. DIVIDER + FOOTER ──────────────────────────────────────────────────
def divider():
    H = 24
    body = (f'<rect x="0" y="11.5" width="{W}" height="1" fill="{GREEN_LO}"/>'
            f'<rect x="-200" y="11" width="200" height="2" fill="{GREEN}" filter="url(#glow)"><animate attributeName="x" values="-200;{W}" dur="4s" repeatCount="indefinite"/></rect>')
    write("divider.svg", svg(W, H, body, "", "divider"))


def footer():
    H = 330
    x = 32
    steps = [("Initiating secure channel", "OK"), ("Negotiating handshake (TLS 1.3)", "OK"), ("Routing to inbox", "OK")]
    out, t = [], .3
    for s, ok in steps:
        segs = [("> ", "a"), (s + " " + "." * (40 - len(s)) + " ", "gd"), (f"[{ok}]", "g b")]
        out.append(appear(x, 66 + len(out) * LH, segs, t)); t += .45
    big = "LET'S BUILD SOMETHING INTELLIGENT"
    by = 66 + 3 * LH + 60
    out.append(f'<g style="animation:show .4s {t:.2f}s both"><text class="vt g" x="{x}" y="{by}">{big}</text></g>')
    bw = len(big) * 46 * .4
    out.append(f'<rect class="blink" x="{x + bw + 8:.0f}" y="{by - 34}" width="20" height="38" fill="{GREEN}"/>')
    sub = "Hiring an engineer, or need an AI product, app or site built and ranked? I reply within a day."
    out.append(appear(x, by + 40, [(sub, "gh")], t + .3))
    ticker = "   ◆   ".join(s["title"].upper() for s in CFG["services"]) + "   ◆   "
    tkw = len(ticker) * 12 * .6
    tk = escape(ticker * (int(W / tkw) + 2))
    out.append(f'<g class="mq"><text class="t gd" x="0" y="{H - 16}" style="font-size:12px">{tk}</text></g>')
    css = fonts_css({"JB": "".join(s for s, _ in steps) + ".[]OK" + sub + ticker, "JBB": "[OK]", "VT": big}) + f"""
    .vt{{font:400 46px 'VT',monospace;letter-spacing:0}}
    .mq{{animation:mq {tkw/50:.1f}s linear infinite}} @keyframes mq{{to{{transform:translateX(-{tkw:.1f}px)}}}}"""
    body = "".join(out) + f'<rect x="0" y="{H - 38}" width="{W}" height="1" fill="{LINE}"/>'
    write("footer.svg", svg(W, H, window(W, H, "./contact.sh --secure", body, rain=True), css, f"{big} — {sub}"))


if __name__ == "__main__":
    print("Building assets…")
    header(); terminal(); services(); stack(); stats(); achievements(); activity(); divider(); footer()
    for s in SECTIONS:
        section(*s)
    for i, p in enumerate(CFG["projects"]):
        project(p, i)
    print("Done.")

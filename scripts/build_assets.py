#!/usr/bin/env python3
"""Builds the animated SVG assets for the profile README from profile.config.json (+ stats.json).

Style: dark editorial — ink surfaces, film grain, Instrument Serif display type over Geist, a single acid-lime
accent and slow, purposeful motion. Every asset paints its own background, so it reads the same in GitHub
light and dark mode.

Usage:  pip install fonttools brotli && python scripts/build_assets.py
Fonts are subset per SVG and embedded as base64 woff2, so they render inside GitHub's <img> sandbox
(GitHub strips external resources and scripts, but keeps CSS + SMIL animation). Text is measured with the
real font metrics, so layouts stay tight when you edit the config.
"""
import base64, io, json, math, os, random, textwrap
from datetime import date, timedelta
from xml.sax.saxutils import escape
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")
CFG = json.load(open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8"))
STATS_PATH = os.path.join(ROOT, "stats.json")
STATS = json.load(open(STATS_PATH, encoding="utf-8")) if os.path.exists(STATS_PATH) else None

# ── design tokens ─────────────────────────────────────────────────────────
INK, CARD, RAISE = "#09090b", "#0d0d10", "#141418"
LINE, LINE2 = "#1f1f25", "#2c2c34"
TEXT, MUTED, DIM = "#f4f4f5", "#a1a1aa", "#5f5f6b"
LIME, LIME_DK = "#c8f542", "#1a2008"
W = 1200

FONT_FILES = {
    ("Serif", 400, "normal"): "instrument-serif-latin-400-normal.woff2",
    ("Serif", 400, "italic"): "instrument-serif-latin-400-italic.woff2",
    ("Geist", 400, "normal"): "geist-sans-latin-400-normal.woff2",
    ("Geist", 500, "normal"): "geist-sans-latin-500-normal.woff2",
    ("Geist", 600, "normal"): "geist-sans-latin-600-normal.woff2",
    ("Mono", 400, "normal"): "geist-mono-latin-400-normal.woff2",
    ("Mono", 500, "normal"): "geist-mono-latin-500-normal.woff2",
}
SERIF, SERIF_I = ("Serif", 400, "normal"), ("Serif", 400, "italic")
SANS, SANS_M, SANS_B = ("Geist", 400, "normal"), ("Geist", 500, "normal"), ("Geist", 600, "normal")
MONO, MONO_M = ("Mono", 400, "normal"), ("Mono", 500, "normal")
_fonts = {}


def font(key):
    if key not in _fonts:
        _fonts[key] = TTFont(os.path.join(FONTS, FONT_FILES[key]))
    return _fonts[key]


def measure(text, key, size, tracking=0.0):
    """Advance width of `text` in px, from the font's real metrics."""
    f = font(key); cmap = f.getBestCmap(); hmtx = f["hmtx"]; upem = f["head"].unitsPerEm
    space = cmap.get(32)
    return sum(hmtx[cmap.get(ord(ch), space)][0] for ch in text) * size / upem + tracking * len(text)


def fonts_css(spec):
    """spec: {font_key: text_used} → @font-face rules with per-SVG subsets."""
    css = []
    for (fam, weight, style), text in spec.items():
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
        f = TTFont(os.path.join(FONTS, FONT_FILES[(fam, weight, style)]))
        s = subset.Subsetter(opts); s.populate(text=text + " 0123456789.,·—→↗"); s.subset(f)
        buf = io.BytesIO(); f.flavor = "woff2"; f.save(buf)
        css.append(f"@font-face{{font-family:'{fam}';font-weight:{weight};font-style:{style};"
                   f"src:url(data:font/woff2;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}")
    return "".join(css)


DEFS = f"""
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/>
  <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .07 0"/></filter>
<filter id="blur" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="60"/></filter>
<filter id="glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3"/></filter>
<linearGradient id="hair" x1="0" x2="1"><stop offset="0" stop-color="{LINE2}" stop-opacity="0"/><stop offset=".15" stop-color="{LINE2}"/><stop offset=".85" stop-color="{LINE2}"/><stop offset="1" stop-color="{LINE2}" stop-opacity="0"/></linearGradient>
<linearGradient id="sheen" x1="0" x2="1"><stop offset="0" stop-color="{LIME}" stop-opacity="0"/><stop offset=".5" stop-color="{LIME}" stop-opacity=".9"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#ffffff" stroke-opacity=".035"/></pattern>
"""

BASE_CSS = ("@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
            ".in{animation:in 1s cubic-bezier(.16,1,.3,1) both}"
            "@keyframes in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}")


def svg(w, h, body, css, title, r=28):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title><style>{css}{BASE_CSS}</style><defs>{DEFS}"
            f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="{r}"/></clipPath></defs>'
            f'<g clip-path="url(#frame)">{body}</g>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="{LINE}"/></svg>')


def surface(w, h, glow=(None, None), grid=False):
    """Ink background, optional engineering grid, one soft lime glow and film grain."""
    gx, gy = glow
    g = (f'<ellipse cx="{gx}" cy="{gy}" rx="280" ry="160" fill="{LIME}" opacity=".07" filter="url(#blur)"/>' if gx is not None else "")
    grid_svg = f'<rect width="{w}" height="{h}" fill="url(#grid)"/>' if grid else ""
    return (f'<rect width="{w}" height="{h}" fill="{CARD}"/>{grid_svg}{g}'
            f'<rect width="{w}" height="{h}" filter="url(#grain)"/>')


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"  ✓ assets/{name}  ({len(content)//1024} KB)")


def rich(line):
    """'plain *accent* plain' → [(text, italic)] segments."""
    parts = line.split("*")
    return [(p, i % 2 == 1) for i, p in enumerate(parts) if p]


def rich_tspans(line):
    return "".join(f'<tspan class="em">{escape(t)}</tspan>' if it else escape(t) for t, it in rich(line))


def heading(num, label, note, y=64, x=56, w=W):
    """Editorial section heading: (01) mono index, serif title, right-aligned note, hairline."""
    nx = x + measure(f"({num})", MONO, 13, 1) + 18
    return (f'<text class="idx" x="{x}" y="{y - 6}">({num})</text>'
            f'<text class="h2" x="{nx:.0f}" y="{y}">{escape(label)}</text>'
            f'<text class="note" x="{w - x}" y="{y - 6}" text-anchor="end">{escape(note)}</text>'
            f'<rect x="{x}" y="{y + 26}" width="{w - 2*x}" height="1" fill="{LINE2}"/>'
            f'<rect x="{x}" y="{y + 25.5}" width="120" height="2" fill="url(#sheen)">'
            f'<animate attributeName="x" values="{x - 120};{w - x}" dur="7s" repeatCount="indefinite"/></rect>')


HEAD_CSS = (f".idx{{font:400 13px 'Mono',monospace;fill:{LIME};letter-spacing:1px}}"
            f".h2{{font:400 46px 'Serif',serif;fill:{TEXT};letter-spacing:-.5px}}"
            f".note{{font:400 12px 'Mono',monospace;fill:{DIM};letter-spacing:1.5px;text-transform:uppercase}}")


def head_fonts(num, label, note):
    return {MONO: f"({num})" + note.upper(), SERIF: label}


def merge(*specs):
    out = {}
    for s in specs:
        for k, v in s.items():
            out[k] = out.get(k, "") + v
    return out


def fmt(n):
    return f"{n:,}"


# ── 1. HERO ───────────────────────────────────────────────────────────────
def hero():
    H = 500
    name, title, status, roles = CFG["name"], CFG["title"], CFG["status"], CFG["roles"]
    facts = list(CFG["facts"])
    if STATS:
        facts.append({"k": "Last 12 months", "v": f"{fmt(STATS['year_contributions'])} contributions"})
    n, step = len(roles), 3.6
    cyc = n * step; on = 100 / n
    role_css = "".join(f".r{i}{{opacity:0;animation:role {cyc}s ease-in-out infinite {i*step - cyc:.1f}s}}" for i in range(n))
    role_css += (f"@keyframes role{{0%{{opacity:0;transform:translateY(8px)}}{on*.12:.2f}%{{opacity:1;transform:none}}"
                 f"{on*.86:.2f}%{{opacity:1;transform:none}}{on:.2f}%{{opacity:0;transform:translateY(-8px)}}100%{{opacity:0}}}}")

    # Constellation: a retrieval graph — nodes light up as queries travel the edges.
    rnd = random.Random(7)
    cx0, cy0 = 960, 205
    nodes = []
    while len(nodes) < 26:
        a, d = rnd.uniform(0, 2 * math.pi), 150 * math.sqrt(rnd.random())
        x, y = cx0 + d * math.cos(a) * 1.25, cy0 + d * math.sin(a)
        if all(math.hypot(x - p[0], y - p[1]) > 34 for p in nodes):
            nodes.append((x, y))
    edges = set()
    for i, (x, y) in enumerate(nodes):
        near = sorted(range(len(nodes)), key=lambda j: math.hypot(nodes[j][0] - x, nodes[j][1] - y))[1:3]
        for j in near:
            edges.add(tuple(sorted((i, j))))
    edges = sorted(edges)
    lines = "".join(f'<line x1="{nodes[a][0]:.1f}" y1="{nodes[a][1]:.1f}" x2="{nodes[b][0]:.1f}" y2="{nodes[b][1]:.1f}" stroke="#ffffff" stroke-opacity=".09"/>' for a, b in edges)
    dots = []
    for i, (x, y) in enumerate(nodes):
        r = 2.2 if i % 5 else 3.4
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{MUTED}" opacity=".55"/>'
                    f'<circle class="lit" style="animation-delay:{(i * 0.71) % 9:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="{r + .4}" fill="{LIME}"/>')
    pulses = []
    for k, (a, b) in enumerate(edges[::3][:9]):
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        dur = 2.6 + (k % 4) * .7
        pulses.append(f'<circle r="2.4" fill="{LIME}" filter="url(#glow)"><animateMotion dur="{dur:.1f}s" begin="{k*.45:.2f}s" repeatCount="indefinite" '
                      f'path="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"/></circle>')
    graph = (f'<g class="in" style="animation-delay:.5s">{lines}{"".join(dots)}{"".join(pulses)}'
             f'<circle cx="{cx0}" cy="{cy0}" r="190" fill="none" stroke="#ffffff" stroke-opacity=".05" stroke-dasharray="2 7"/></g>')

    # Status pill (top-right)
    pill_w = measure(status, SANS_M, 13) + 52
    px = W - 56 - pill_w
    pill = (f'<rect x="{px:.0f}" y="44" width="{pill_w:.0f}" height="34" rx="17" fill="{RAISE}" stroke="{LINE2}"/>'
            f'<circle class="ping" cx="{px + 20:.0f}" cy="61" r="4" fill="{LIME}"/><circle cx="{px + 20:.0f}" cy="61" r="4" fill="{LIME}"/>'
            f'<text class="pill" x="{px + 34:.0f}" y="65.5">{escape(status)}</text>')

    # Name: last word in italic lime-free serif, trailing lime dot.
    first, _, last = name.rpartition(" ")
    name_svg = (f'<text class="name in" style="animation-delay:.1s" x="52" y="230">{escape(first)} '
                f'<tspan class="it">{escape(last)}</tspan><tspan fill="{LIME}">.</tspan></text>')
    roles_svg = "".join(f'<text class="role r{i}" x="56" y="318">{escape(r)}</text>' for i, r in enumerate(roles))

    cols = len(facts); cw = (W - 112) / cols
    fact_svg = [f'<rect x="56" y="{H - 118}" width="{W - 112}" height="1" fill="{LINE2}"/>']
    for i, f in enumerate(facts):
        x = 56 + i * cw
        if i:
            fact_svg.append(f'<rect x="{x - 1:.0f}" y="{H - 118}" width="1" height="74" fill="{LINE}"/>')
        pad = 0 if i == 0 else 24
        fact_svg.append(f'<text class="fk" x="{x + pad:.0f}" y="{H - 82}">{escape(f["k"].upper())}</text>'
                        f'<text class="fv" x="{x + pad:.0f}" y="{H - 54}">{escape(f["v"])}</text>')

    brand = f"{CFG['username']}  /  portfolio  /  {date.today().year}"
    css = fonts_css({SERIF: first, SERIF_I: last, SANS_M: status + title, SANS: "".join(f["v"] for f in facts),
                     MONO: "".join(roles) + brand + "".join(f["k"].upper() for f in facts) + "→"}) + f"""
    .name{{font:400 128px 'Serif',serif;fill:{TEXT};letter-spacing:-3px}} .it{{font-style:italic}}
    .title{{font:500 22px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-.3px}}
    .role{{font:400 15px 'Mono',monospace;fill:{LIME}}}
    .pill{{font:500 13px 'Geist',sans-serif;fill:{TEXT}}}
    .brand{{font:400 12px 'Mono',monospace;fill:{DIM};letter-spacing:2px;text-transform:uppercase}}
    .fk{{font:400 11px 'Mono',monospace;fill:{DIM};letter-spacing:1.8px}} .fv{{font:400 16px 'Geist',sans-serif;fill:{TEXT}}}
    .ping{{animation:ping 2.2s cubic-bezier(0,0,.2,1) infinite;transform-box:fill-box;transform-origin:center}}
    @keyframes ping{{75%,100%{{transform:scale(2.8);opacity:0}}}}
    .lit{{opacity:0;animation:lit 9s ease-in-out infinite}} @keyframes lit{{0%,100%{{opacity:0}}6%,14%{{opacity:1}}24%{{opacity:0}}}}
    {role_css} @media (prefers-reduced-motion: reduce){{.r0{{opacity:1!important}}}}"""
    tx = 56 + measure(title, SANS_M, 22, -.3) + 14
    body = f"""{surface(W, H, glow=(980, 120), grid=True)}
    {graph}
    <text class="brand" x="56" y="66">{escape(brand)}</text>
    {pill}
    {name_svg}
    <g class="in" style="animation-delay:.25s"><text class="title" x="56" y="284">{escape(title)}</text>
      <rect x="{tx:.0f}" y="276" width="28" height="1" fill="{LINE2}"/></g>
    <g class="in" style="animation-delay:.35s">{roles_svg}</g>
    <g class="in" style="animation-delay:.45s">{''.join(fact_svg)}</g>"""
    write("hero.svg", svg(W, H, body, css, f"{name} — {title}"))


# ── 2. LINK BUTTONS ───────────────────────────────────────────────────────
def buttons():
    for b in CFG["links"]:
        label, primary = b["label"], b.get("primary", False)
        size, h = 14, 44
        w = round(measure(label, SANS_M, size) + measure(" ↗", SANS_M, size) + 40)
        fg, bg, stroke = (INK, LIME, LIME) if primary else (TEXT, CARD, LINE2)
        css = fonts_css({SANS_M: label + "↗"}) + f".b{{font:500 {size}px 'Geist',sans-serif;fill:{fg}}}"
        body = (f'<rect width="{w}" height="{h}" fill="{bg}"/>'
                f'<text class="b" x="20" y="27.5">{escape(label)}<tspan dx="6" opacity=".7">↗</tspan></text>')
        out = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(label)}">'
               f"<title>{escape(label)}</title><style>{css}</style><defs><clipPath id='c'><rect width='{w}' height='{h}' rx='22'/></clipPath></defs>"
               f'<g clip-path="url(#c)">{body}</g><rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="21.5" fill="none" stroke="{stroke}"/></svg>')
        write(f"btn-{b['slug']}.svg", out)


# ── 3. ABOUT ──────────────────────────────────────────────────────────────
def about():
    a = CFG["about"]
    H = 520
    st = "".join(f'<text class="st" x="56" y="{170 + i*58}">{rich_tspans(l)}</text>' for i, l in enumerate(a["statement"]))
    plain = "".join(t for l in a["statement"] for t, it in rich(l) if not it)
    ital = "".join(t for l in a["statement"] for t, it in rich(l) if it)

    def panel(x, y, w, label, items, delay):
        rows = "".join(f'<text class="li" x="{x + 24}" y="{y + 72 + i*30}"><tspan fill="{LIME}">—</tspan>  {escape(t)}</text>' for i, t in enumerate(items))
        return (f'<g class="in" style="animation-delay:{delay}s"><rect x="{x}" y="{y}" width="{w}" height="{48 + 30*len(items) + 16}" rx="18" fill="{RAISE}" stroke="{LINE}"/>'
                f'<text class="pl" x="{x + 24}" y="{y + 36}">{escape(label.upper())}</text>{rows}</g>')
    px, pw = 56, W - 112
    half = (pw - 20) / 2
    panels = panel(px, 396, half, "For recruiters", a["recruiters"], .2) + panel(px + half + 20, 396, half, "For clients", a["clients"], .3)
    H = 396 + 48 + 30 * max(len(a["recruiters"]), len(a["clients"])) + 16 + 48
    css = fonts_css(merge(head_fonts("01", "About", "who I am"), {SERIF: plain, SERIF_I: ital, SANS: "".join(a["recruiters"] + a["clients"]) + "—",
                                                                   MONO: "FOR RECRUITERSFOR CLIENTS"})) + HEAD_CSS + f"""
    .st{{font:400 44px 'Serif',serif;fill:{TEXT};letter-spacing:-.6px}} .em{{font-style:italic;fill:{LIME}}}
    .pl{{font:400 11.5px 'Mono',monospace;fill:{DIM};letter-spacing:2px}} .li{{font:400 15.5px 'Geist',sans-serif;fill:#d4d4d8}}"""
    body = f"""{surface(W, H, glow=(1100, 40))}
    {heading("01", "About", "who I am")}
    <g class="in">{st}</g>
    {panels}"""
    write("about.svg", svg(W, H, body, css, "About — " + " ".join(t for l in a["statement"] for t, _ in rich(l))))


# ── 4. SERVICES ───────────────────────────────────────────────────────────
def services():
    svc = CFG["services"]
    top, rh = 130, 96
    H = top + rh * len(svc) + 40
    n = len(svc); cyc = n * 2.2
    rows, rules = [], []
    for i, s in enumerate(svc):
        y = top + i * rh
        pts = "   ·   ".join(s["points"])
        rules.append(f".s{i}{{animation:hl {cyc:.1f}s ease-in-out infinite {i*2.2:.1f}s}}")
        rows.append(f"""<g class="in" style="animation-delay:{.08*i:.2f}s">
          <rect class="hl s{i}" x="40" y="{y}" width="{W-80}" height="{rh - 8}" rx="16" fill="{RAISE}"/>
          <rect class="hl s{i}" x="40" y="{y + 22}" width="3" height="{rh - 52}" rx="1.5" fill="{LIME}"/>
          <text class="no" x="64" y="{y + 40}">{i+1:02d}</text>
          <text class="t" x="128" y="{y + 44}">{escape(s['title'])}</text>
          <text class="p" x="128" y="{y + 72}">{escape(pts)}</text>
          <text class="ar s{i}" x="{W - 72}" y="{y + 52}" text-anchor="end">→</text>
          <rect x="56" y="{y + rh - 4}" width="{W - 112}" height="1" fill="{LINE}"/></g>""")
    pct = 100 / n
    css = fonts_css(merge(head_fonts("02", "What I build", "services"), {SERIF: "".join(s["title"] for s in svc),
                                                                         SANS: "".join("".join(s["points"]) for s in svc) + "→", MONO: "0123456789"})) + HEAD_CSS + f"""
    .no{{font:400 13px 'Mono',monospace;fill:{DIM}}} .t{{font:400 32px 'Serif',serif;fill:{TEXT};letter-spacing:-.3px}}
    .p{{font:400 15px 'Geist',sans-serif;fill:{MUTED}}} .ar{{font:400 22px 'Geist',sans-serif;fill:{LIME};opacity:.0}}
    .hl{{opacity:0}}
    @keyframes hl{{0%{{opacity:0}}{pct*.18:.1f}%,{pct*.82:.1f}%{{opacity:1}}{pct:.1f}%,100%{{opacity:0}}}}
    {''.join(rules)}"""
    body = f"""{surface(W, H, glow=(120, H - 40))}
    {heading("02", "What I build", "services")}
    {''.join(rows)}"""
    write("services.svg", svg(W, H, body, css, "What I build — " + ", ".join(s["title"] for s in svc)))


# ── 5. PROJECTS ───────────────────────────────────────────────────────────
def projects_heading():
    H = 120
    css = fonts_css(head_fonts("03", "Selected work", "click a card")) + HEAD_CSS
    write("section-projects.svg", svg(W, H, f"{surface(W, H)}{heading('03', 'Selected work', 'click a card', y=70)}", css, "Selected work"))


def project(p, idx):
    PW, PH = 590, 340
    desc = textwrap.wrap(p["desc"], 56)[:3]
    tags = "  /  ".join(p["tags"][:4])
    num = f"{idx + 1:02d}"
    css = fonts_css({SERIF: p["title"] + num, SANS: "".join(desc), SANS_M: "↗",
                     MONO: p["label"].upper() + p["role"] + p["metric"] + tags.upper()}) + f"""
    .lb{{font:400 11.5px 'Mono',monospace;fill:{LIME};letter-spacing:2px}} .mt{{font:400 12px 'Mono',monospace;fill:{MUTED}}}
    .t{{font:400 38px 'Serif',serif;fill:{TEXT};letter-spacing:-.6px}} .r{{font:400 13px 'Mono',monospace;fill:{DIM}}}
    .d{{font:400 15.5px 'Geist',sans-serif;fill:#c4c4cc}} .tg{{font:400 11.5px 'Mono',monospace;fill:{MUTED};letter-spacing:1.4px}}
    .big{{font:400 230px 'Serif',serif;fill:none;stroke:#ffffff;stroke-opacity:.06;stroke-width:1}}
    .go{{font:500 20px 'Geist',sans-serif;fill:{INK}}}
    .orb{{animation:orb 3s ease-in-out infinite}} @keyframes orb{{50%{{transform:translate(3px,-3px)}}}}"""
    mw = measure(p["metric"], MONO, 12)
    body = f"""{surface(PW, PH, glow=(PW - 40, 20))}
    <text class="big" x="{PW - 20}" y="{PH + 40}" text-anchor="end">{num}</text>
    <circle cx="44" cy="52" r="3.5" fill="{LIME}"/>
    <text class="lb" x="58" y="56.5">{escape(p['label'].upper())}</text>
    <rect x="{PW - 40 - mw - 28:.0f}" y="36" width="{mw + 28:.0f}" height="30" rx="15" fill="{RAISE}" stroke="{LINE2}"/>
    <text class="mt" x="{PW - 40 - 14}" y="55.5" text-anchor="end">{escape(p['metric'])}</text>
    <text class="t in" x="38" y="124">{escape(p['title'])}</text>
    <text class="r" x="40" y="152">{escape(p['role'])}</text>
    {''.join(f'<text class="d" x="40" y="{194 + i*24}">{escape(l)}</text>' for i, l in enumerate(desc))}
    <rect x="40" y="{PH - 76}" width="{PW - 80}" height="1" fill="{LINE}"/>
    <text class="tg" x="40" y="{PH - 38}">{escape(tags.upper())}</text>
    <g class="orb"><circle cx="{PW - 62}" cy="{PH - 44}" r="22" fill="{LIME}"/>
      <text class="go" x="{PW - 62}" y="{PH - 37}" text-anchor="middle">↗</text></g>"""
    write(f"project-{p['slug']}.svg", svg(PW, PH, body, css, f"{p['title']} — {p['desc']}", r=24))


# ── 6. STACK ──────────────────────────────────────────────────────────────
def stack():
    layers = CFG["stack"]
    top, rh = 140, 66
    H = top + rh * (len(layers) - 1) + 64
    label_x, chip_x0 = 104, 300
    rows = []
    for i, L in enumerate(layers):
        y = top + i * rh
        x = chip_x0; chips = []
        for t in L["items"]:
            w = measure(t, SANS, 14.5) + 30
            if x + w > W - 56:
                break
            chips.append(f'<rect x="{x:.0f}" y="{y - 22}" width="{w:.0f}" height="38" rx="19" fill="{RAISE}" stroke="{LINE2}"/>'
                         f'<text class="c" x="{x + 15:.0f}" y="{y + 2}">{escape(t)}</text>')
            x += w + 10
        rows.append(f'<g class="in" style="animation-delay:{.08*i:.2f}s">'
                    f'<circle cx="72" cy="{y - 3}" r="6" fill="{CARD}" stroke="{LINE2}"/><circle class="node" style="animation-delay:{i*.6:.1f}s" cx="72" cy="{y - 3}" r="3" fill="{LIME}"/>'
                    f'<text class="ly" x="{label_x}" y="{y + 1}">{escape(L["layer"].upper())}</text>{"".join(chips)}</g>')
    y0, y1 = top - 3, top + rh * (len(layers) - 1) - 3
    css = fonts_css(merge(head_fonts("04", "The stack", "from model to market"), {SANS: "".join("".join(L["items"]) for L in layers),
                                                                                MONO: "".join(L["layer"].upper() for L in layers)})) + HEAD_CSS + f"""
    .ly{{font:400 12px 'Mono',monospace;fill:{MUTED};letter-spacing:2px}} .c{{font:400 14.5px 'Geist',sans-serif;fill:#e4e4e7}}
    .node{{animation:node {len(layers)*.6:.1f}s ease-in-out infinite;opacity:.25}} @keyframes node{{0%,30%,100%{{opacity:.25}}10%{{opacity:1}}}}"""
    body = f"""{surface(W, H, glow=(W - 100, H - 20))}
    {heading("04", "The stack", "from model to market")}
    <rect x="71.5" y="{y0}" width="1" height="{y1 - y0}" fill="{LINE2}"/>
    <circle r="3.5" fill="{LIME}" filter="url(#glow)"><animateMotion dur="{len(layers)*.6:.1f}s" repeatCount="indefinite" path="M72,{y0} L72,{y1}"/></circle>
    {''.join(rows)}"""
    write("stack.svg", svg(W, H, body, css, "Tech stack — " + "; ".join(f"{L['layer']}: {', '.join(L['items'])}" for L in layers)))


# ── 7. STATS (incl. private & org repos) ──────────────────────────────────
def stats():
    if not STATS:
        H = 260
        msg = "Add the METRICS_TOKEN secret and run the “Profile stats” workflow."
        css = fonts_css(merge(head_fonts("05", "Activity", "private + public"), {SANS: msg})) + HEAD_CSS + f".m{{font:400 16px 'Geist',sans-serif;fill:{MUTED}}}"
        write("stats.svg", svg(W, H, f"{surface(W, H)}{heading('05', 'Activity', 'private + public')}<text class='m' x='56' y='170'>{escape(msg)}</text>", css, "GitHub activity"))
        return
    s = STATS
    H = 690
    cal = s["calendar"]; start = date.fromisoformat(s["calendar_start"])
    weeks = -(-len(cal) // 7)
    gap = 4; step = int((W - 112 + gap) // weeks); cell = step - gap
    gx, gy = 56 + (W - 112 - (weeks * step - gap)) / 2, 372
    nz = sorted(c for c in cal if c)
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]
    def level(c):
        return 0 if c == 0 else 1 + sum(c > t for t in q)
    fills = {0: "#1e1e24", 1: "#3a4a12", 2: "#6a8a1c", 3: "#a3d12e", 4: LIME}
    cells, months, last_m = [], [], None
    for i, c in enumerate(cal):
        wk, dy = divmod(i, 7)
        d = start + timedelta(days=i)
        x, y = gx + wk * step, gy + dy * step
        cls = f"w{wk}" + (" today" if i == len(cal) - 1 else "")
        cells.append(f'<rect class="{cls}" x="{x:.0f}" y="{y:.0f}" width="{cell}" height="{cell}" rx="4" fill="{fills[level(c)]}"/>')
        if dy == 0 and d.month != last_m and d.day <= 7:
            if wk < weeks - 2:
                months.append(f'<text class="mo" x="{x:.0f}" y="{gy - 14}">{d.strftime("%b").upper()}</text>')
            last_m = d.month
    wrules = "".join(f".w{w}{{animation:pop .6s cubic-bezier(.16,1,.3,1) {.25 + w*.018:.3f}s both}}" for w in range(weeks))

    kpis = [(fmt(s["commits"]), "Commits", f"since {s['since']}"), (fmt(s["prs_merged"]), "PRs merged", "all repos"),
            (fmt(s["repos"]), "Repositories", f"{s['private_repos']} private"), (f"{s['streak_longest']}d", "Longest streak", f"current {s['streak_current']}d")]
    kx0, kw = 520, (W - 56 - 520) / 4
    kp = []
    for i, (v, k, sub) in enumerate(kpis):
        x = kx0 + i * kw
        kp.append(f'<g class="in" style="animation-delay:{.1 + .07*i:.2f}s"><rect x="{x - 1:.0f}" y="146" width="1" height="132" fill="{LINE}"/>'
                  f'<text class="kv" x="{x + 22:.0f}" y="214">{escape(v)}</text>'
                  f'<text class="kk" x="{x + 22:.0f}" y="246">{escape(k.upper())}</text>'
                  f'<text class="ks" x="{x + 22:.0f}" y="268">{escape(sub)}</text></g>')

    # Language spectrum: lime for the lead language, then a graphite ramp.
    langs = [l for l in s["languages"] if l["pct"] >= .5][:6]
    tot = sum(l["pct"] for l in langs) or 1
    ramp = [LIME, "#e4e4e7", "#a1a1aa", "#71717a", "#52525b", "#3f3f46"]
    bx, by, bw = 56, 584, W - 112
    seg, leg, x, lx = [], [], bx, 56
    for i, l in enumerate(langs):
        w = bw * l["pct"] / tot
        seg.append(f'<rect x="{x:.1f}" y="{by}" width="{max(w - 3, 2):.1f}" height="10" rx="3" fill="{ramp[i]}"/>')
        x += w
        lab = f'{l["name"]} {l["pct"]:g}%'
        leg.append(f'<rect x="{lx}" y="{by + 36}" width="8" height="8" rx="2" fill="{ramp[i]}"/><text class="lg" x="{lx + 16}" y="{by + 44}">{escape(l["name"])}<tspan fill="{DIM}">  {l["pct"]:g}%</tspan></text>')
        lx += measure(lab, MONO, 12.5) + 52
    foot = f"Updated {s['updated']}  ·  public + private + organisation repositories  ·  refreshed daily"
    hero_n = fmt(s["year_contributions"])
    legend_txt = "".join(f'{l["name"]}{l["pct"]:g}%' for l in langs)
    css = fonts_css(merge(head_fonts("05", "Activity", "incl. private & org work"),
                          {SERIF: hero_n + "".join(k[0] for k in kpis), SERIF_I: "contributions",
                           MONO: "".join(k[1].upper() + k[2] for k in kpis) + legend_txt + foot + "JANFEBMARAPRMAYJUNJULAUGSEPOCTNOVDEC LESS MORE in the last 12 months · best day"})) + HEAD_CSS + f"""
    .hn{{font:400 112px 'Serif',serif;fill:{TEXT};letter-spacing:-3px}} .hc{{font:400 italic 30px 'Serif',serif;fill:{LIME}}}
    .hs{{font:400 12px 'Mono',monospace;fill:{DIM};letter-spacing:1px}}
    .kv{{font:400 52px 'Serif',serif;fill:{TEXT};letter-spacing:-1px}} .kk{{font:400 11px 'Mono',monospace;fill:{MUTED};letter-spacing:1.8px}}
    .ks{{font:400 12px 'Mono',monospace;fill:{DIM}}} .mo{{font:400 10.5px 'Mono',monospace;fill:{DIM};letter-spacing:1.5px}}
    .lg{{font:400 12.5px 'Mono',monospace;fill:{TEXT}}} .ft{{font:400 11.5px 'Mono',monospace;fill:{DIM};letter-spacing:.5px}}
    @keyframes pop{{from{{opacity:0}}to{{opacity:1}}}} {wrules}
    .today{{animation:today 2s ease-in-out infinite!important}} @keyframes today{{50%{{opacity:.35}}}}"""
    legend_scale = "".join(f'<rect x="{W - 56 - 5*15 + i*15 - 40}" y="{gy + 7*step + 8}" width="11" height="11" rx="3" fill="{fills[i]}"/>' for i in range(5))
    body = f"""{surface(W, H, glow=(200, 160))}
    {heading("05", "Activity", "incl. private & org work")}
    <g class="in"><text class="hn" x="50" y="238">{hero_n}</text>
      <text class="hc" x="56" y="286">contributions</text>
      <text class="hs" x="{72 + measure('contributions', SERIF_I, 30):.0f}" y="284">  in the last 12 months · best day {s['best_day']}</text></g>
    {''.join(kp)}
    {''.join(months)}{''.join(cells)}
    <text class="ft" x="{W - 56 - 5*15 - 50}" y="{gy + 7*step + 18}" text-anchor="end">LESS</text>{legend_scale}<text class="ft" x="{W - 56}" y="{gy + 7*step + 18}" text-anchor="end">MORE</text>
    {''.join(seg)}{''.join(leg)}
    <rect x="56" y="{H - 52}" width="{W - 112}" height="1" fill="{LINE}"/>
    <text class="ft" x="56" y="{H - 24}">{escape(foot)}</text>"""
    write("stats.svg", svg(W, H, body, css, f"GitHub activity incl. private repos: {hero_n} contributions in the last 12 months, "
                                            f"{fmt(s['commits'])} commits, {fmt(s['prs_merged'])} PRs merged, {s['repos']} repositories"))


# ── 8. CONTACT / FOOTER ───────────────────────────────────────────────────
def contact():
    H = 420
    l1, l1i, l2 = "Let's build something", "intelligent.", "Hiring an engineer, or need an AI product, app or site built and ranked? I reply within a day."
    cta = "Start a conversation"
    ticker = "   ✦   ".replace("✦", "·").join(s["title"] for s in CFG["services"]) + "   ·   "
    tw = measure(ticker, MONO, 13, 2)
    reps = int(W / tw) + 2
    cw = measure(cta, SANS_M, 15) + measure("  →", SANS_M, 15) + 48
    css = fonts_css(merge(head_fonts("06", "Contact", "reply within 24h"),
                          {SERIF: l1, SERIF_I: l1i, SANS: l2, SANS_M: cta + "→", MONO: ticker.upper()})) + HEAD_CSS + f"""
    .a{{font:400 84px 'Serif',serif;fill:{TEXT};letter-spacing:-2px}} .ai{{font-style:italic;fill:{LIME}}}
    .b{{font:400 17px 'Geist',sans-serif;fill:{MUTED}}} .cta{{font:500 15px 'Geist',sans-serif;fill:{INK}}}
    .tk{{font:400 13px 'Mono',monospace;fill:{DIM};letter-spacing:2px}}
    .mq{{animation:mq {tw/40:.1f}s linear infinite}} @keyframes mq{{to{{transform:translateX(-{tw:.1f}px)}}}}
    .nudge{{animation:nudge 1.8s ease-in-out infinite}} @keyframes nudge{{50%{{transform:translateX(5px)}}}}"""
    body = f"""{surface(W, H, glow=(600, H + 40), grid=True)}
    {heading("06", "Contact", "reply within 24h")}
    <text class="a in" x="52" y="214">{escape(l1)} <tspan class="ai">{escape(l1i)}</tspan></text>
    <text class="b in" style="animation-delay:.15s" x="56" y="258">{escape(l2)}</text>
    <g class="in" style="animation-delay:.25s"><rect x="56" y="284" width="{cw:.0f}" height="48" rx="24" fill="{LIME}"/>
      <text class="cta" x="80" y="313">{escape(cta)}<tspan class="nudge" dx="8">→</tspan></text></g>
    <rect x="0" y="{H - 54}" width="{W}" height="1" fill="{LINE}"/>
    <g class="mq"><text class="tk" x="0" y="{H - 22}">{escape((ticker * reps).upper())}</text></g>"""
    write("contact.svg", svg(W, H, body, css, f"{l1} {l1i} {l2}"))


if __name__ == "__main__":
    print("Building assets…")
    hero(); buttons(); about(); services(); projects_heading(); stack(); stats(); contact()
    for i, p in enumerate(CFG["projects"]):
        project(p, i)
    print("Done.")

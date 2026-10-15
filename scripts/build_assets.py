#!/usr/bin/env python3
"""Builds the animated SVG assets for the profile README from profile.config.json.

Style: light, minimal, professional — white surfaces, 1px zinc hairlines, deep accents, Geist type, calm motion.
Every asset has its own solid background, so it stays readable in GitHub light AND dark mode.

Usage:  pip install fonttools brotli && python scripts/build_assets.py
Fonts are subset per SVG and embedded as base64 woff2, so they render inside GitHub's <img> sandbox
(GitHub strips external resources and scripts, but keeps CSS + SMIL animation).
"""
import base64, io, json, os, re, textwrap
from xml.sax.saxutils import escape
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "scripts", "fonts")
OUT = os.path.join(ROOT, "assets")
CFG = json.load(open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8"))
_SP = os.path.join(ROOT, "stats.json")
STATS = json.load(open(_SP, encoding="utf-8")) if os.path.exists(_SP) else None

# ── design tokens ─────────────────────────────────────────────────────────
BG, CARD, SURFACE, LINE = "#ffffff", "#ffffff", "#f8fafc", "#e4e4e7"
TEXT, MUTED, DIM = "#18181b", "#52525b", "#a1a1aa"
INDIGO, VIOLET, CYAN, EMERALD, AMBER = "#4f46e5", "#7c3aed", "#0891b2", "#059669", "#b45309"
ACCENTS = [INDIGO, VIOLET, CYAN, EMERALD]

FONT_FILES = {
    ("Geist", 400): "geist-sans-latin-400-normal.woff2",
    ("Geist", 500): "geist-sans-latin-500-normal.woff2",
    ("Geist", 600): "geist-sans-latin-600-normal.woff2",
    ("Geist", 700): "geist-sans-latin-700-normal.woff2",
    ("GeistMono", 400): "geist-mono-latin-400-normal.woff2",
    ("GeistMono", 500): "geist-mono-latin-500-normal.woff2",
}


def font_face(family, weight, text):
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
    f = TTFont(os.path.join(FONTS, FONT_FILES[(family, weight)]))
    s = subset.Subsetter(opts); s.populate(text=text + " 0123456789·—→●_›/|:.-#"); s.subset(f)
    buf = io.BytesIO(); f.flavor = "woff2"; f.save(buf)
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{base64.b64encode(buf.getvalue()).decode()}) format('woff2');}}")


def fonts_css(spec):
    return "".join(font_face(fam, w, txt) for (fam, w), txt in spec.items())


def tw(text, size, mono=False):
    """Rough text width estimate for sizing pills/chips."""
    return len(text) * size * (0.6 if mono else 0.55)


DEFS = f"""
<linearGradient id="aurora" x1="0" x2="1"><stop offset="0" stop-color="{INDIGO}"/><stop offset=".5" stop-color="{VIOLET}"/><stop offset="1" stop-color="{CYAN}"/></linearGradient>
<linearGradient id="hair" x1="0" x2="1"><stop offset="0" stop-color="#a1a1aa" stop-opacity="0"/><stop offset=".5" stop-color="#a1a1aa" stop-opacity=".55"/><stop offset="1" stop-color="#a1a1aa" stop-opacity="0"/></linearGradient>
<linearGradient id="glint" x1="0" x2="1"><stop offset="0" stop-color="{VIOLET}" stop-opacity="0"/><stop offset=".5" stop-color="{VIOLET}" stop-opacity=".6"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient>
<linearGradient id="silver" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#09090b"/><stop offset="1" stop-color="#3f3f46"/></linearGradient>
<linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="260" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".8"/><stop offset="1" stop-color="#fff" stop-opacity="0"/><animateTransform attributeName="gradientTransform" type="translate" values="-400 0;1600 0" dur="6s" repeatCount="indefinite"/></linearGradient>
<filter id="blur" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="48"/></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>
<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#18181b" opacity=".08"/></pattern>
"""

BASE_CSS = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"


def svg(w, h, body, css, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f"<title>{escape(title)}</title><style>{css}{BASE_CSS}</style><defs>{DEFS}</defs>{body}</svg>")


DARK = {  # light token → GitHub-dark counterpart
    "#ffffff": "#0d1117", "#f8fafc": "#161b22", "#e4e4e7": "#30363d", "#18181b": "#e6edf3", "#52525b": "#9da7b3",
    "#a1a1aa": "#6e7681", "#09090b": "#ffffff", "#3f3f46": "#b1bac4", "#4f46e5": "#818cf8", "#7c3aed": "#a78bfa",
    "#0891b2": "#22d3ee", "#059669": "#34d399", "#b45309": "#fbbf24", "#f1f5f9": "#161b22", "#e0e7ff": "#1e1b4b",
    "#a5b4fc": "#3730a3", "#4338ca": "#a5b4fc",
}


def write(name, content):
    """Writes the light asset to assets/ and a dark-palette twin to assets/dark/."""
    os.makedirs(os.path.join(OUT, "dark"), exist_ok=True)
    dark = re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: DARK.get(m.group(0).lower(), m.group(0)), content)
    for path, data in ((os.path.join(OUT, name), content), (os.path.join(OUT, "dark", name), dark)):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(data)
    print(f"  ✓ assets/{name} + dark  ({len(content)//1024} KB)")


def card(w, h, r=18, glint=True, dur=7):
    """Base card: white fill, 1px hairline, faint top highlight and an optional travelling glint."""
    g = (f'<rect class="glint" x="-200" y="0" width="200" height="1.5" fill="url(#glint)">'
         f'<animate attributeName="x" values="-200;{w + 200}" dur="{dur}s" repeatCount="indefinite"/></rect>') if glint else ""
    return (f'<rect width="{w}" height="{h}" rx="{r}" fill="{CARD}"/>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="{LINE}"/>'
            f'{g}')


def tracer(w, h, r, dur=6.0, phase=0.0, width=1.5):
    """A short aurora-coloured light that travels around a card's border."""
    return (f'<rect x=".75" y=".75" width="{w-1.5}" height="{h-1.5}" rx="{r}" fill="none" stroke="url(#aurora)" stroke-width="{width}" '
            f'pathLength="1000" stroke-dasharray="90 910" stroke-linecap="round">'
            f'<animate attributeName="stroke-dashoffset" values="0;-1000" dur="{dur}s" begin="-{phase:.2f}s" repeatCount="indefinite"/></rect>')


# ── 1. HEADER ─────────────────────────────────────────────────────────────
def header():
    W, H = 1200, 340
    name, title, status, roles = CFG["name"], CFG["title"], CFG["status"], CFG["roles"]
    n, step = len(roles), 3.4
    cyc = n * step
    on = 100 / n
    role_css = "".join(f".r{i}{{opacity:0;animation:role {cyc}s ease-in-out infinite {i*step - cyc:.1f}s}}" for i in range(n))
    role_css += (f"@keyframes role{{0%{{opacity:0;transform:translateY(6px)}}{on*.1:.2f}%{{opacity:1;transform:none}}"
                 f"{on*.86:.2f}%{{opacity:1;transform:none}}{on:.2f}%{{opacity:0;transform:translateY(-6px)}}100%{{opacity:0}}}}")
    roles_svg = "".join(f'<text class="role r{i}" x="80" y="246"><tspan fill="{VIOLET}">› </tspan>{escape(r)}</text>' for i, r in enumerate(roles))

    css = fonts_css({("Geist", 600): name, ("Geist", 500): title + status, ("GeistMono", 400): "".join(roles) + "github.com/" + CFG["username"]}) + f"""
    .name{{font:600 68px 'Geist',sans-serif;letter-spacing:-2.5px}}
    .title{{font:500 26px 'Geist',sans-serif;letter-spacing:-.4px}}
    .role{{font:400 17px 'GeistMono',monospace;fill:{MUTED}}}
    .pill{{font:500 14px 'Geist',sans-serif;fill:{TEXT}}}
    .url{{font:400 12px 'GeistMono',monospace;fill:{DIM};letter-spacing:.5px}}
    .in{{animation:in .9s cubic-bezier(.2,.7,.2,1) both}} .d1{{animation-delay:.12s}} .d2{{animation-delay:.24s}} .d3{{animation-delay:.36s}}
    @keyframes in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
    .ping{{animation:ping 2s cubic-bezier(0,0,.2,1) infinite;transform-origin:99px 76px}}
    @keyframes ping{{75%,100%{{transform:scale(2.6);opacity:0}}}}
    .spin1{{animation:spin 26s linear infinite;transform-origin:950px 170px}}
    .spin2{{animation:spin 40s linear infinite reverse;transform-origin:950px 170px}}
    .spin3{{animation:spin 16s linear infinite;transform-origin:950px 170px}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    .breathe{{animation:breathe 5s ease-in-out infinite;transform-origin:950px 170px}}
    @keyframes breathe{{50%{{transform:scale(1.12);opacity:.65}}}}
    {role_css} @media (prefers-reduced-motion: reduce){{.r0{{opacity:1!important}}}}"""

    cx, cy = 950, 170
    pill_w = tw(status, 14) + 54
    rings = f"""
      <circle class="breathe" cx="{cx}" cy="{cy}" r="70" fill="{VIOLET}" opacity=".16" filter="url(#blur)"/>
      <circle cx="{cx}" cy="{cy}" r="58" fill="none" stroke="#18181b" stroke-opacity=".08"/>
      <circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="#18181b" stroke-opacity=".07"/>
      <circle cx="{cx}" cy="{cy}" r="134" fill="none" stroke="#18181b" stroke-opacity=".12" stroke-dasharray="2 6"/>
      <g class="spin1"><circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="url(#aurora)" stroke-width="1.6" stroke-dasharray="120 484" stroke-linecap="round"/>
        <circle cx="{cx + 96}" cy="{cy}" r="4" fill="{CYAN}"/><circle cx="{cx + 96}" cy="{cy}" r="9" fill="{CYAN}" opacity=".25" filter="url(#soft)"/></g>
      <g class="spin2"><circle cx="{cx}" cy="{cy}" r="134" fill="none" stroke="url(#aurora)" stroke-width="1.2" stroke-dasharray="70 772" stroke-linecap="round" opacity=".8"/>
        <circle cx="{cx}" cy="{cy - 134}" r="3.5" fill="{INDIGO}"/></g>
      <g class="spin3"><circle cx="{cx}" cy="{cy}" r="58" fill="none" stroke="url(#aurora)" stroke-width="1.4" stroke-dasharray="40 325" stroke-linecap="round"/>
        <circle cx="{cx - 58}" cy="{cy}" r="3" fill="{VIOLET}"/></g>
      <circle cx="{cx}" cy="{cy}" r="22" fill="{CARD}" stroke="#18181b" stroke-opacity=".12"/>
      <circle cx="{cx}" cy="{cy}" r="7" fill="url(#aurora)"/>"""
    body = f"""
    <defs><clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
      <radialGradient id="fadeR" cx=".75" cy=".4" r=".7"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <mask id="dm"><rect width="{W}" height="{H}" fill="url(#fadeR)"/></mask></defs>
    <g clip-path="url(#frame)">
      <rect width="{W}" height="{H}" fill="{BG}"/>
      <rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#dm)"/>
      <g opacity=".38">
        <ellipse cx="820" cy="40" rx="260" ry="120" fill="{INDIGO}" opacity=".45" filter="url(#blur)">
          <animate attributeName="cx" values="820;900;820" dur="18s" repeatCount="indefinite"/></ellipse>
        <ellipse cx="1060" cy="120" rx="200" ry="110" fill="{VIOLET}" opacity=".35" filter="url(#blur)">
          <animate attributeName="cy" values="120;70;120" dur="14s" repeatCount="indefinite"/></ellipse>
        <ellipse cx="640" cy="-20" rx="220" ry="90" fill="{CYAN}" opacity=".22" filter="url(#blur)">
          <animate attributeName="cx" values="640;560;640" dur="22s" repeatCount="indefinite"/></ellipse>
      </g>
      {rings}
      <g class="in">
        <rect x="80" y="58" width="{pill_w:.0f}" height="36" rx="18" fill="{SURFACE}" stroke="{LINE}"/>
        <circle class="ping" cx="99" cy="76" r="4" fill="{EMERALD}"/><circle cx="99" cy="76" r="4" fill="{EMERALD}"/>
        <text class="pill" x="114" y="81">{escape(status)}</text>
      </g>
      <text class="name in d1" x="76" y="168" fill="url(#silver)">{escape(name)}</text>
      <text class="name in d1" x="76" y="168" fill="url(#shine)">{escape(name)}</text>
      <text class="title in d2" x="80" y="208" fill="url(#aurora)">{escape(title)}</text>
      <g class="in d3">{roles_svg}</g>
      <text class="url" x="80" y="302">github.com/{escape(CFG['username'])}</text>
    </g>
    <rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="20" fill="none" stroke="{LINE}"/>
    {tracer(W, H, 20, dur=12, width=1.8)}
    """
    write("header.svg", svg(W, H, body, css, f"{name} — {title}"))


# ── 2. TERMINAL ───────────────────────────────────────────────────────────
def terminal():
    W = 1200
    rows = []
    blocks = list(CFG["terminal"])
    if STATS:
        langs = " · ".join(f"{l['name']} {round(l['pct'])}%" for l in STATS["languages"][:3])
        blocks.insert(len(blocks) - 1, {"cmd": "gh stats --include-private", "out": [
            f"activity:  {STATS['year_contributions']:,} contributions in the last 12 months",
            f"repos:     {STATS['repos']} ({STATS['private_repos']} private) · {STATS['prs_merged']:,} PRs merged",
            f"langs:     {langs}"]})
    for blk in blocks:
        rows.append(("cmd", blk["cmd"])); rows += [("out", o) for o in blk["out"]]
    LH, TOP = 30, 92
    H = TOP + LH * len(rows) + 40
    alltxt = "".join(r[1] for r in rows) + "vamshi@ai ~ % zsh terminal"
    t, items, rules = 0.4, [], []
    for i, (kind, txt) in enumerate(rows):
        y = TOP + i * LH
        if kind == "cmd":
            d = max(.45, len(txt) * .05)
            rules.append(f".t{i}{{animation:type {d:.2f}s steps({max(len(txt),1)}) {t:.2f}s both}}")
            items.append(f'<g class="t{i}"><text x="40" y="{y}" class="m"><tspan fill="{VIOLET}">vamshi@ai</tspan><tspan fill="{DIM}"> ~ % </tspan><tspan fill="{TEXT}" font-weight="500">{escape(txt)}</tspan></text></g>')
            t += d + .25
        else:
            col = EMERALD if txt.startswith("●") else (AMBER if txt.startswith("⎇") else MUTED)
            if ":" in txt and not txt.startswith(("●", "⎇", "Vamshi")):
                k, v = txt.split(":", 1); inner = f'<tspan fill="{CYAN}">{escape(k)}:</tspan><tspan fill="{TEXT}">{escape(v)}</tspan>'
            elif txt.startswith("Vamshi"):
                inner = f'<tspan fill="{TEXT}">{escape(txt)}</tspan>'
            else:
                inner = escape(txt)
            rules.append(f".t{i}{{animation:show .4s ease-out {t:.2f}s both}}")
            items.append(f'<text x="40" y="{y}" class="m t{i}" fill="{col}">{inner}</text>')
            t += .2
    ye = TOP + len(rows) * LH
    rules.append(f".end{{animation:show .2s {t:.2f}s both}}")
    css = fonts_css({("GeistMono", 400): alltxt, ("GeistMono", 500): "terminal — zsh"}) + f"""
    .m{{font:400 16.5px 'GeistMono',monospace;white-space:pre}} .bar{{font:500 12.5px 'GeistMono',monospace;fill:{MUTED}}}
    .cur{{animation:blink 1.1s steps(1) infinite}} @keyframes blink{{50%{{opacity:0}}}}
    @keyframes type{{from{{clip-path:inset(0 100% 0 0)}}to{{clip-path:inset(0 0 0 0)}}}}
    @keyframes show{{from{{opacity:0;transform:translateY(4px)}}to{{opacity:1;transform:none}}}}
    {''.join(rules)}"""
    body = f"""
    {card(W, H, 16)}
    <rect x="1" y="1" width="{W-2}" height="46" rx="15" fill="{SURFACE}"/><rect x="1" y="30" width="{W-2}" height="17" fill="{SURFACE}"/>
    <line x1="1" y1="47.5" x2="{W-1}" y2="47.5" stroke="{LINE}"/>
    <circle cx="28" cy="24" r="6" fill="#ff5f57"/><circle cx="48" cy="24" r="6" fill="#febc2e"/><circle cx="68" cy="24" r="6" fill="#28c840"/>
    <text class="bar" x="{W/2}" y="28" text-anchor="middle">terminal — zsh</text>
    {''.join(items)}
    <g class="end"><text x="40" y="{ye}" class="m"><tspan fill="{VIOLET}">vamshi@ai</tspan><tspan fill="{DIM}"> ~ % </tspan></text>
      <rect class="cur" x="184" y="{ye - 15}" width="9" height="19" rx="1" fill="{TEXT}"/></g>"""
    write("terminal.svg", svg(W, H, body, css, "whoami — terminal intro"))


# ── 3. SECTION HEADINGS ───────────────────────────────────────────────────
SECTIONS = [("about", "01", "About"), ("services", "02", "What I build"), ("projects", "03", "Featured work"),
            ("stack", "04", "Tech stack"), ("stats", "05", "GitHub activity"), ("feed", "06", "Latest writing & activity"),
            ("guestbook", "07", "Guestbook"), ("contact", "08", "Let's talk")]


def section(slug, num, label):
    W, H = 1200, 64
    css = fonts_css({("Geist", 600): label, ("GeistMono", 400): num}) + f"""
    .n{{font:400 13px 'GeistMono',monospace;fill:{MUTED};letter-spacing:1px}} .h{{font:600 30px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-.8px}}"""
    lw = tw(label, 30) + 92
    body = f"""
    <defs><linearGradient id="fadeline" x1="0" x2="1"><stop offset="0" stop-color="#18181b" stop-opacity=".14"/><stop offset="1" stop-color="#18181b" stop-opacity="0"/></linearGradient></defs>
    {card(W, H, 14, glint=False)}
    <rect x="20" y="21" width="34" height="22" rx="11" fill="{SURFACE}" stroke="{LINE}"/>
    <text class="n" x="37" y="36.5" text-anchor="middle">{num}</text>
    <text class="h" x="68" y="43">{escape(label)}</text>
    <rect x="{lw:.0f}" y="32" width="{W - lw - 24:.0f}" height="1" fill="url(#fadeline)"/>
    <rect x="{lw:.0f}" y="31.5" width="90" height="2" rx="1" fill="url(#aurora)" opacity=".9">
      <animate attributeName="x" values="{lw:.0f};{W-114};{lw:.0f}" dur="9s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0;.9;0" dur="4.5s" repeatCount="indefinite"/></rect>"""
    write(f"section-{slug}.svg", svg(W, H, body, css, label))


# ── 4. SERVICES ───────────────────────────────────────────────────────────
ICON = {
    "agent": '<rect x="-11" y="-8" width="22" height="17" rx="5" fill="none" stroke="{c}" stroke-width="1.8"/><circle cx="-4.5" cy="0" r="1.8" fill="{c}"/><circle cx="4.5" cy="0" r="1.8" fill="{c}"/><line x1="0" y1="-8" x2="0" y2="-13" stroke="{c}" stroke-width="1.8"/><circle cx="0" cy="-14.5" r="2" fill="{c}"><animate attributeName="opacity" values="1;.25;1" dur="1.6s" repeatCount="indefinite"/></circle>',
    "rag": '<ellipse cx="0" cy="-8" rx="10" ry="3.6" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M-10 -8 V8 A10 3.6 0 0 0 10 8 V-8" fill="none" stroke="{c}" stroke-width="1.8"/><path d="M-10 0 A10 3.6 0 0 0 10 0" fill="none" stroke="{c}" stroke-width="1.8"/>',
    "mobile": '<rect x="-8" y="-13" width="16" height="26" rx="3.5" fill="none" stroke="{c}" stroke-width="1.8"/><line x1="-2.5" y1="9" x2="2.5" y2="9" stroke="{c}" stroke-width="1.8" stroke-linecap="round"><animate attributeName="opacity" values="1;.3;1" dur="2s" repeatCount="indefinite"/></line>',
    "web": '<rect x="-13" y="-10" width="26" height="20" rx="3" fill="none" stroke="{c}" stroke-width="1.8"/><line x1="-13" y1="-4" x2="13" y2="-4" stroke="{c}" stroke-width="1.8"/><polyline points="-7,6 -2,1 2,4 8,-1" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"><animate attributeName="opacity" values="1;.3;1" dur="2.2s" repeatCount="indefinite"/></polyline>',
    "spark": '<path d="M0 -13 L3 -3 L13 0 L3 3 L0 13 L-3 3 L-13 0 L-3 -3 Z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"><animateTransform attributeName="transform" type="scale" values="1;.82;1" dur="2.4s" repeatCount="indefinite"/></path>',
    "stack": '<path d="M0 -12 L12 -6 L0 0 L-12 -6 Z" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/><path d="M-12 0 L0 6 L12 0" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"><animate attributeName="opacity" values="1;.3;1" dur="2.4s" repeatCount="indefinite"/></path><path d="M-12 6 L0 12 L12 6" fill="none" stroke="{c}" stroke-width="1.8" stroke-linejoin="round"/>',
}


def services():
    svc = CFG["services"]
    cols = 3 if len(svc) % 3 == 0 else 2
    W, gap, ch = 1200, 24, 236
    rows = -(-len(svc) // cols)
    H = rows * ch + (rows - 1) * gap
    cw = (W - gap * (cols - 1)) / cols
    css = fonts_css({("Geist", 600): "".join(s["title"] for s in svc), ("Geist", 400): "".join("".join(s["points"]) for s in svc)}) + f"""
    .h{{font:600 20px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-.3px}} .p{{font:400 15.5px 'Geist',sans-serif;fill:{MUTED}}}"""
    out = []
    for i, s in enumerate(svc):
        x, y, c = (i % cols) * (cw + gap), (i // cols) * (ch + gap), ACCENTS[i % 4]
        pts = "".join(f'<circle cx="34" cy="{158 + j*28 - 5}" r="2.5" fill="{c}"/><text class="p" x="48" y="{158 + j*28}">{escape(p)}</text>' for j, p in enumerate(s["points"]))
        out.append(f"""
        <g transform="translate({x:.0f},{y})"><defs><clipPath id="sc{i}"><rect width="{cw:.0f}" height="{ch}" rx="16"/></clipPath></defs>
          <g clip-path="url(#sc{i})">{card(round(cw), ch, 16, dur=8 + i*1.5)}{tracer(round(cw), ch, 16, dur=9, phase=i*1.5)}
          <circle cx="{cw - 40:.0f}" cy="30" r="80" fill="{c}" opacity=".07" filter="url(#blur)"/></g>
          <rect x="28" y="28" width="44" height="44" rx="12" fill="{c}" fill-opacity=".08" stroke="{c}" stroke-opacity=".35"><animate attributeName="fill-opacity" values=".06;.2;.06" dur="3.2s" begin="-{i*.53:.2f}s" repeatCount="indefinite"/></rect>
          <g transform="translate(50,50)">{ICON[s['icon']].format(c=c)}</g>
          <text class="h" x="28" y="108">{escape(s['title'])}</text>
          <line x1="28" y1="126.5" x2="{cw-28:.0f}" y2="126.5" stroke="{LINE}"/>
          {pts}</g>""")
    write("services.svg", svg(W, H, "".join(out), css, "What I build"))


# ── 5. PROJECT CARDS ──────────────────────────────────────────────────────
def project(p, idx):
    W, H = 590, 300
    c = ACCENTS[idx % 4]
    desc = textwrap.wrap(p["desc"], 62)[:3]
    tags = p["tags"][:4]
    css = fonts_css({("Geist", 600): p["title"], ("Geist", 400): "".join(desc), ("Geist", 500): p["label"] + "".join(tags) + "View project →",
                     ("GeistMono", 400): p["role"] + p["metric"]}) + f"""
    .t{{font:600 25px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-.6px}} .r{{font:400 13.5px 'GeistMono',monospace;fill:{c}}}
    .d{{font:400 15.5px 'Geist',sans-serif;fill:{MUTED}}} .tag{{font:500 12.5px 'Geist',sans-serif;fill:#3f3f46}}
    .lbl{{font:500 12.5px 'Geist',sans-serif;fill:{TEXT}}} .m{{font:400 12.5px 'GeistMono',monospace;fill:{MUTED}}}
    .v{{font:500 14px 'Geist',sans-serif;fill:{TEXT}}}
    .arrow{{animation:nudge 1.8s ease-in-out infinite}} @keyframes nudge{{50%{{transform:translateX(4px)}}}}"""
    lw, mw = tw(p["label"], 12.5) + 40, tw(p["metric"], 12.5, True) + 26
    tx, chips = 32, []
    for tg in tags:
        w = tw(tg, 12.5) + 24
        chips.append(f'<rect x="{tx:.0f}" y="236" width="{w:.0f}" height="28" rx="8" fill="{SURFACE}" stroke="{LINE}"/>'
                     f'<text class="tag" x="{tx + w/2:.0f}" y="254.5" text-anchor="middle">{escape(tg)}</text>')
        tx += w + 8
    body = f"""
    <defs><clipPath id="cc"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
    <g clip-path="url(#cc)">{card(W, H, 18, dur=6 + idx)}{tracer(W, H, 18, dur=7, phase=idx*1.7)}
      <ellipse cx="{W-30}" cy="10" rx="160" ry="90" fill="{c}" opacity=".08" filter="url(#blur)"/>
      <rect width="{W}" height="{H}" fill="url(#dots)" opacity=".6"/></g>
    <rect x="32" y="30" width="{lw:.0f}" height="28" rx="14" fill="{SURFACE}" stroke="{LINE}"/>
    <circle cx="47" cy="44" r="3.5" fill="{c}"/>
    <text class="lbl" x="58" y="48.5">{escape(p['label'])}</text>
    <text class="m" x="{W-32}" y="48.5" text-anchor="end">{escape(p['metric'])}</text>
    <text class="t" x="32" y="104">{escape(p['title'])}</text>
    <text class="r" x="32" y="130">{escape(p['role'])}</text>
    {''.join(f'<text class="d" x="32" y="{166 + i*22}">{escape(l)}</text>' for i, l in enumerate(desc))}
    {''.join(chips)}
    <g class="arrow"><text class="v" x="{W-32}" y="255" text-anchor="end">View project →</text></g>"""
    write(f"project-{p['slug']}.svg", svg(W, H, body, css, p["title"]))


# ── 6. DIVIDER + FOOTER ───────────────────────────────────────────────────
def divider():
    W, H = 1200, 24
    body = f"""<rect x="0" y="11.5" width="{W}" height="1" fill="url(#hair)"/>
    <rect x="-160" y="11" width="160" height="2" rx="1" fill="url(#aurora)"><animate attributeName="x" values="-160;{W}" dur="6s" repeatCount="indefinite"/></rect>"""
    write("divider.svg", svg(W, H, body, "", "divider"))


def footer():
    W, H = 1200, 250
    ticker = "   ·   ".join(s["title"] for s in CFG["services"]) + "   ·   "
    tkw = len(ticker) * 13 * 0.6 + len(ticker) * 1.5
    l1, l2 = "Let's build something intelligent.", "Hiring an engineer, or need an AI product, app or site built and ranked? I reply within a day."
    css = fonts_css({("Geist", 600): l1, ("Geist", 400): l2, ("GeistMono", 400): ticker.upper()}) + f"""
    .tk{{font:400 13px 'GeistMono',monospace;fill:{DIM};letter-spacing:1.5px}}
    .mq{{animation:mq {tkw/45:.1f}s linear infinite}} @keyframes mq{{to{{transform:translateX(-{tkw:.1f}px)}}}}
    .a{{font:600 40px 'Geist',sans-serif;letter-spacing:-1.4px}} .b{{font:400 17px 'Geist',sans-serif;fill:{MUTED}}}"""
    body = f"""
    <defs><clipPath id="fc"><rect width="{W}" height="{H}" rx="20"/></clipPath></defs>
    <g clip-path="url(#fc)">{card(W, H, 20)}{tracer(W, H, 20, dur=10)}
      <rect width="{W}" height="{H}" fill="url(#dots)"/>
      <ellipse cx="600" cy="230" rx="380" ry="90" fill="url(#aurora)" opacity=".18" filter="url(#blur)">
        <animate attributeName="rx" values="380;460;380" dur="10s" repeatCount="indefinite"/></ellipse></g>
    <text class="a" x="{W/2}" y="96" text-anchor="middle" fill="url(#silver)">{escape(l1)}</text>
    <text class="b" x="{W/2}" y="134" text-anchor="middle">{escape(l2)}</text>
    <line x1="40" y1="186.5" x2="{W-40}" y2="186.5" stroke="{LINE}"/>
    <g clip-path="url(#fc)"><g class="mq"><text class="tk" x="0" y="222">{escape((ticker * (int(W / tkw) + 2)).upper())}</text></g></g>"""
    write("footer.svg", svg(W, H, body, css, l1))


# ── 7. STATS (incl. private & org repos, from stats.json) ─────────────────
def stats():
    path = os.path.join(ROOT, "stats.json")
    if not os.path.exists(path):
        return
    st = json.load(open(path, encoding="utf-8"))
    W, H = 1200, 490
    from datetime import date, timedelta
    cal, start = st["calendar"], date.fromisoformat(st["calendar_start"])
    weeks = -(-len(cal) // 7)
    gap = 3; step = int((W - 64 + gap) // weeks); cell = step - gap
    gx, gy = 32 + (W - 64 - (weeks * step - gap)) / 2, 232
    nz = sorted(c for c in cal if c)
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]
    heat = ["#f1f5f9", "#e0e7ff", "#a5b4fc", "#6366f1", "#4338ca"]
    cells, months, last_m = [], [], None
    for i, c in enumerate(cal):
        wk, dy = divmod(i, 7); d = start + timedelta(days=i)
        lv = 0 if c == 0 else 1 + sum(c > t for t in q)
        today = ' class="today"' if i == len(cal) - 1 else ""
        cells.append(f'<rect{today} x="{gx + wk*step:.0f}" y="{gy + dy*step:.0f}" width="{cell}" height="{cell}" rx="4" fill="{heat[lv]}"/>')
        if dy == 0 and d.month != last_m and d.day <= 7:
            if wk < weeks - 2:
                months.append(f'<text class="mo" x="{gx + wk*step:.0f}" y="{gy - 10}">{d.strftime("%b")}</text>')
            last_m = d.month
    cols_svg = []
    for wk in range(weeks):
        cols_svg.append(f'<g class="col" style="animation-delay:{.2 + wk*.022:.3f}s">{"".join(cells[wk*7:wk*7+7])}</g>')
    hy = gy + 7 * step
    heat_legend = "".join(f'<rect x="{W - 32 - 50 - (5 - i)*15 + 4}" y="{hy + 8}" width="11" height="11" rx="3" fill="{heat[i]}"/>' for i in range(5))
    heat_svg = (f'{"".join(months)}{"".join(cols_svg)}'
                f'<clipPath id="hm"><rect x="{gx:.0f}" y="{gy}" width="{weeks*step - gap}" height="{7*step - gap}"/></clipPath>'
                f'<g clip-path="url(#hm)"><rect x="{gx - 120:.0f}" y="{gy}" width="120" height="{7*step}" fill="url(#glint)" opacity=".35">'
                f'<animate attributeName="x" values="{gx - 120:.0f};{W}" dur="5s" begin="1.6s" repeatCount="indefinite"/></rect></g>'
                f'<text class="s" x="{W - 32 - 50 - 5*15 - 4}" y="{hy + 18}" text-anchor="end">Less</text>{heat_legend}'
                f'<text class="s" x="{W - 32}" y="{hy + 18}" text-anchor="end">More</text>'
                f'<text class="s" x="{gx:.0f}" y="{hy + 18}">best day {st["best_day"]} · current streak {st["streak_current"]}d</text>')
    kpis = [(f"{st['year_contributions']:,}", "Contributions", "last 12 months"),
            (f"{st['commits']:,}", "Commits", f"since {st['since']}"),
            (f"{st['prs_merged']:,}", "PRs merged", "all repositories"),
            (f"{st['repos']:,}", "Repositories", f"{st['private_repos']} private"),
            (f"{st['streak_longest']}d", "Longest streak", f"current {st['streak_current']}d")]
    langs = [l for l in st["languages"] if l["pct"] >= .5][:5]
    tot = sum(l["pct"] for l in langs) or 1
    cols = [INDIGO, VIOLET, CYAN, EMERALD, AMBER]
    label, upd = "Incl. private & org repos", f"updated {st['updated']}"
    legend = "".join(f"{l['name']}{l['pct']:g}%" for l in langs)
    css = fonts_css({("Geist", 600): "".join(k[0] for k in kpis), ("Geist", 500): label + "".join(k[1] for k in kpis) + legend,
                     ("GeistMono", 400): upd + "".join(k[2] for k in kpis) + legend + "JanFebMarAprMayJunJulAugSepOctNovDec LessMore best day current streak"}) + f"""
    .v{{font:600 40px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-1.2px}} .k{{font:500 14px 'Geist',sans-serif;fill:{TEXT}}}
    .s{{font:400 12.5px 'GeistMono',monospace;fill:{MUTED}}} .lbl{{font:500 12.5px 'Geist',sans-serif;fill:{TEXT}}}
    .m{{font:400 12.5px 'GeistMono',monospace;fill:{MUTED}}} .lg{{font:500 13px 'Geist',sans-serif;fill:{TEXT}}}
    .mo{{font:400 11px 'GeistMono',monospace;fill:{DIM}}}
    .col{{animation:col .7s cubic-bezier(.2,.7,.2,1) both}} @keyframes col{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
    .today{{animation:today 1.6s ease-in-out infinite}} @keyframes today{{50%{{opacity:.3}}}}
    .kin{{animation:col .8s cubic-bezier(.2,.7,.2,1) both}}
    .grow{{animation:grow 1.2s cubic-bezier(.2,.7,.2,1) both;transform-origin:32px 0;animation-delay:.9s}} @keyframes grow{{from{{transform:scaleX(0)}}to{{transform:none}}}}"""
    cw = (W - 64) / len(kpis)
    kp = []
    for i, (v, k, sub) in enumerate(kpis):
        x = 32 + i * cw
        sep = f'<line x1="{x:.0f}" y1="92" x2="{x:.0f}" y2="176" stroke="{LINE}"/>' if i else ""
        pad = 0 if i == 0 else 24
        kp.append(f'<g class="kin" style="animation-delay:{.1 + i*.08:.2f}s">{sep}<text class="v" x="{x + pad:.0f}" y="128">{escape(v)}</text>'
                  f'<text class="k" x="{x + pad:.0f}" y="154">{escape(k)}</text><text class="s" x="{x + pad:.0f}" y="174">{escape(sub)}</text></g>')
    seg, leg, x, lx, bw = [], [], 32, 32, W - 64
    for i, l in enumerate(langs):
        w = bw * l["pct"] / tot
        seg.append(f'<rect x="{x:.1f}" y="422" width="{max(w - 3, 2):.1f}" height="10" rx="3" fill="{cols[i]}"/>')
        x += w
        leg.append(f'<circle cx="{lx + 4}" cy="{460}" r="4" fill="{cols[i]}"/><text class="lg" x="{lx + 16}" y="464.5">{escape(l["name"])}'
                   f'<tspan class="m" dx="6">{l["pct"]:g}%</tspan></text>')
        lx += tw(l["name"], 13) + tw(f"{l['pct']:g}%", 12.5, True) + 50
    lw = tw(label, 12.5) + 40
    body = f"""
    <defs><clipPath id="sc"><rect width="{W}" height="{H}" rx="18"/></clipPath></defs>
    <g clip-path="url(#sc)">{card(W, H, 18)}
      <ellipse cx="{W-60}" cy="10" rx="220" ry="90" fill="{INDIGO}" opacity=".07" filter="url(#blur)"/>
      <rect width="{W}" height="{H}" fill="url(#dots)" opacity=".5"/></g>
    <rect x="32" y="30" width="{lw:.0f}" height="28" rx="14" fill="{SURFACE}" stroke="{LINE}"/>
    <circle cx="47" cy="44" r="3.5" fill="{EMERALD}"/><text class="lbl" x="58" y="48.5">{escape(label)}</text>
    <text class="m" x="{W-32}" y="48.5" text-anchor="end">{escape(upd)}</text>
    {''.join(kp)}
    <line x1="32" y1="196.5" x2="{W-32}" y2="196.5" stroke="{LINE}"/>
    {heat_svg}
    <rect x="32" y="422" width="{bw}" height="10" rx="5" fill="{SURFACE}"/>
    <g class="grow">{''.join(seg)}</g>
    {''.join(leg)}"""
    write("stats.svg", svg(W, H, body, css, "GitHub stats incl. private & org repos: " +
                           ", ".join(f"{v} {k.lower()}" for v, k, _ in kpis)))


# ── 8. ACHIEVEMENTS (tiered trophies from stats.json) ─────────────────────
def achievements():
    if not STATS:
        return
    st = STATS

    def tier(v, s_, a_, b_):
        return "S" if v >= s_ else "A" if v >= a_ else "B" if v >= b_ else "C"

    def short(v):
        return f"{v/1000:.1f}k".replace(".0k", "k") if v >= 1000 else str(v)
    nlang = len([l for l in st["languages"] if l["pct"] >= .5])
    items = [
        ("Committer", short(st["commits"]), "commits", tier(st["commits"], 2000, 1000, 300)),
        ("Shipper", short(st["prs_merged"]), "PRs merged", tier(st["prs_merged"], 500, 200, 50)),
        ("Builder", short(st["repos"]), "repositories", tier(st["repos"], 100, 50, 20)),
        ("Under NDA", short(st["private_repos"]), "private repos", tier(st["private_repos"], 30, 15, 5)),
        ("Marathon", f"{st['streak_longest']}d", "longest streak", tier(st["streak_longest"], 60, 30, 14)),
        ("Polyglot", str(nlang), "languages", tier(nlang, 6, 4, 3)),
    ]
    W, H, n, gap = 1200, 236, len(items), 16
    cw = (W - gap * (n - 1)) / n
    tcol = {"S": AMBER, "A": VIOLET, "B": INDIGO, "C": CYAN}
    css = fonts_css({("Geist", 600): "".join(i[1] + i[3] for i in items), ("Geist", 500): "".join(i[0] for i in items),
                     ("GeistMono", 400): "".join(i[2] for i in items)}) + f"""
    .v{{font:600 30px 'Geist',sans-serif;fill:{TEXT};letter-spacing:-.8px}} .k{{font:500 15px 'Geist',sans-serif;fill:{TEXT}}}
    .s{{font:400 11.5px 'GeistMono',monospace;fill:{MUTED}}} .t{{font:600 15px 'Geist',sans-serif}}
    .pop{{animation:pop .7s cubic-bezier(.2,.7,.2,1.3) both}} @keyframes pop{{from{{opacity:0;transform:scale(.85) translateY(8px)}}to{{opacity:1;transform:none}}}}
    .spin{{animation:spin 8s linear infinite;transform-box:fill-box;transform-origin:center}} @keyframes spin{{to{{transform:rotate(360deg)}}}}"""
    out = []
    for i, (k, v, sub, t) in enumerate(items):
        x, c, cx = i * (cw + gap), tcol[t], cw / 2
        out.append(f"""<g transform="translate({x:.0f},0)"><g class="pop" style="animation-delay:{i*.09:.2f}s;transform-origin:{cx:.0f}px 100px">
          <defs><clipPath id="ac{i}"><rect width="{cw:.0f}" height="{H}" rx="16"/></clipPath></defs>
          <g clip-path="url(#ac{i})">{card(round(cw), H, 16, dur=7 + i)}{tracer(round(cw), H, 16, dur=8, phase=i*1.3)}
            <ellipse cx="{cx:.0f}" cy="40" rx="80" ry="50" fill="{c}" opacity=".1" filter="url(#blur)"/></g>
          <circle cx="{cx:.0f}" cy="66" r="34" fill="{c}" fill-opacity=".08"/>
          <circle class="spin" cx="{cx:.0f}" cy="66" r="34" fill="none" stroke="{c}" stroke-width="2" stroke-dasharray="60 154" stroke-linecap="round"/>
          <circle cx="{cx:.0f}" cy="66" r="25" fill="{CARD}" stroke="{c}" stroke-opacity=".35"/>
          <text class="t" x="{cx:.0f}" y="71.5" text-anchor="middle" fill="{c}">{t}</text>
          <text class="v" x="{cx:.0f}" y="146" text-anchor="middle">{escape(v)}</text>
          <text class="k" x="{cx:.0f}" y="176" text-anchor="middle">{escape(k)}</text>
          <text class="s" x="{cx:.0f}" y="200" text-anchor="middle">{escape(sub)}</text></g></g>""")
    write("achievements.svg", svg(W, H, "".join(out), css,
                                  "Achievements: " + ", ".join(f"{k} ({v} {s_}, tier {t})" for k, v, s_, t in items)))


# ── 9. WEEKLY ACTIVITY CHART ──────────────────────────────────────────────
def activity():
    if not STATS:
        return
    from datetime import date, timedelta
    cal, start = STATS["calendar"], date.fromisoformat(STATS["calendar_start"])
    weeks = [sum(cal[i:i + 7]) for i in range(0, len(cal), 7)]
    W, H = 1200, 340
    x0, x1, y0, y1 = 64, W - 40, 70, H - 60
    nice = max(40, -(-max(weeks) // 40) * 40)
    pts = [(x0 + i * (x1 - x0) / (len(weeks) - 1), y1 - w * (y1 - y0) / nice) for i, w in enumerate(weeks)]
    line = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        mx = (ax + bx) / 2
        line += f" C{mx:.1f},{ay:.1f} {mx:.1f},{by:.1f} {bx:.1f},{by:.1f}"
    area = line + f" L{x1},{y1} L{x0},{y1} Z"
    pk = max(range(len(weeks)), key=lambda i: weeks[i])
    px, py = pts[pk]
    grid = "".join(f'<line x1="{x0}" y1="{y1 - f*(y1-y0):.0f}" x2="{x1}" y2="{y1 - f*(y1-y0):.0f}" stroke="{LINE}" stroke-dasharray="3 5"/>'
                   f'<text class="ax" x="{x0 - 12}" y="{y1 - f*(y1-y0) + 4:.0f}" text-anchor="end">{int(nice*f)}</text>'
                   for f in (0, .25, .5, .75, 1))
    months, last = [], None
    for i in range(len(weeks)):
        d = start + timedelta(days=i * 7)
        if d.month != last and i < len(weeks) - 2:
            months.append(f'<text class="ax" x="{pts[i][0]:.0f}" y="{y1 + 26}" text-anchor="middle">{d.strftime("%b")}</text>')
            last = d.month
    title, sub, peak = "Weekly contributions", "last 12 months · public + private", f"peak {weeks[pk]} / week"
    css = fonts_css({("Geist", 600): title, ("GeistMono", 400): sub + peak + "JanFebMarAprMayJunJulAugSepOctNovDec"}) + f"""
    .h{{font:600 18px 'Geist',sans-serif;fill:{TEXT}}} .sub{{font:400 12.5px 'GeistMono',monospace;fill:{MUTED}}}
    .ax{{font:400 11px 'GeistMono',monospace;fill:{DIM}}} .pk{{font:400 12px 'GeistMono',monospace;fill:{TEXT}}}
    .draw{{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.4s cubic-bezier(.4,0,.2,1) .2s forwards}} @keyframes draw{{to{{stroke-dashoffset:0}}}}
    .fade{{animation:fade 1.2s ease 1.4s both}} @keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
    .ring{{animation:ring 2s ease-out 2.4s infinite;transform-box:fill-box;transform-origin:center}} @keyframes ring{{from{{transform:scale(1);opacity:.6}}to{{transform:scale(3.2);opacity:0}}}}
    @media (prefers-reduced-motion: reduce){{.draw{{stroke-dashoffset:0}}}}"""
    body = f"""
    <defs><clipPath id="wc"><rect width="{W}" height="{H}" rx="18"/></clipPath>
      <linearGradient id="fillg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{INDIGO}" stop-opacity=".28"/><stop offset="1" stop-color="{INDIGO}" stop-opacity="0"/></linearGradient></defs>
    <g clip-path="url(#wc)">{card(W, H, 18)}<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".5"/></g>
    <text class="h" x="32" y="40">{title}</text><text class="sub" x="{W - 32}" y="40" text-anchor="end">{escape(sub)}</text>
    {grid}{''.join(months)}
    <path class="fade" d="{area}" fill="url(#fillg)"/>
    <path class="draw" d="{line}" fill="none" stroke="url(#aurora)" stroke-width="2.5" stroke-linecap="round" pathLength="1"/>
    <g class="fade"><circle class="ring" cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{VIOLET}"/><circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{VIOLET}" stroke="{CARD}" stroke-width="2"/>
      <text class="pk" x="{min(px + 12, W - 140):.0f}" y="{py - 12:.0f}">{escape(peak)}</text></g>"""
    write("activity.svg", svg(W, H, body, css, f"Weekly contributions over the last 12 months, peak {weeks[pk]} per week"))


if __name__ == "__main__":
    print("Building assets…")
    header(); terminal(); services(); divider(); footer(); stats(); achievements(); activity()
    for s in SECTIONS: section(*s)
    for i, p in enumerate(CFG["projects"]): project(p, i)
    print("Done.")

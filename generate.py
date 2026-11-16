#!/usr/bin/env python3
"""
SHADOW FEED: animated art for the 3abch9leu profile README (dark / anonymous / hacker).

Nothing here is static. Every run (a GitHub Action, every 3 hours) redraws the page from:
  - the real time in Tunisia -> 4 moods a day (night / dawn / day / dusk), always dark
  - the day of the year      -> 1 of 4 scenes: matrix, radar, web, blackout
  - the date                 -> a new random arrangement + a new session id + a new line
  - the moon                 -> real phase, shown as a faint dark moon at night
The hero also carries a small ENCRYPTED line: the daily quote in base64. Decode it if you can.
"""
import os, math, random, json, base64, urllib.request, datetime as dt
from xml.sax.saxutils import escape as xesc
from zoneinfo import ZoneInfo

OWNER = os.environ.get("GITHUB_REPOSITORY_OWNER", "3abch9leu")
OUT = os.environ.get("OUT_DIR", "art")
TZ = ZoneInfo("Africa/Tunis")

now = dt.datetime.now(TZ)
if os.environ.get("FORCE_HOUR"):
    now = now.replace(hour=int(os.environ["FORCE_HOUR"]), minute=int(os.environ.get("FORCE_MIN", 0)))
YDAY = now.timetuple().tm_yday
SCENES = ["matrix", "radar", "web", "blackout"]
SCENE = SCENES[YDAY % len(SCENES)]
if os.environ.get("FORCE_SCENE"): SCENE = os.environ["FORCE_SCENE"]

def phase_of(h):
    if 5 <= h < 8: return "dawn"
    if 8 <= h < 17: return "day"
    if 17 <= h < 20: return "dusk"
    return "night"
PHASE = phase_of(now.hour)

# every palette stays DARK. Only the glow colour and the mood change.
PAL = {
    "night": dict(bg=("#010208", "#050a14", "#0a1022"), a1="#00ff9c", a2="#9d4edd", a3="#ff0054", txt="#dffcf0", threat="HIGH"),
    "dawn":  dict(bg=("#07010d", "#150521", "#2a0a2a"), a1="#ff3d71", a2="#b266ff", a3="#ffb36b", txt="#ffe8ee", threat="RISING"),
    "day":   dict(bg=("#010609", "#04141a", "#082229"), a1="#00e5ff", a2="#00ff9c", a3="#9d4edd", txt="#dff9ff", threat="LOW"),
    "dusk":  dict(bg=("#070112", "#1a0630", "#33093a"), a1="#c77dff", a2="#ff0054", a3="#00ff9c", txt="#f6e8ff", threat="ELEVATED"),
}
P = PAL[PHASE]
MONO = "'Courier New',Courier,monospace"

def seed(extra=0): return now.year * 1000 + YDAY * 7 + extra
SESSION = "0x%04X" % (random.Random(seed(99)).randint(0, 0xFFFF))

# ---------- real moon phase ----------
def moon_phase():
    jd = now.astimezone(dt.timezone.utc).timestamp() / 86400.0 + 2440587.5
    return ((jd - 2451550.1) / 29.530588853) % 1.0
MOON = moon_phase()
MOON_PCT = round((1 - math.cos(2 * math.pi * MOON)) / 2 * 100)

def moon_glyph(cx, cy, r):
    ph = MOON if MOON <= 0.5 else 1 - MOON
    k = math.cos(2 * math.pi * ph)
    rx = abs(k) * r
    lit = f"M0 {-r} A{r} {r} 0 0 1 0 {r} A{rx:.2f} {r} 0 0 {0 if k > 0 else 1} 0 {-r} Z"
    flip = ' transform="scale(-1 1)"' if MOON > 0.5 else ""
    return (f'<g transform="translate({cx:.0f} {cy:.0f})" opacity="0.8"><circle r="{r*2.2:.0f}" fill="url(#mglow)"/>'
            f'<circle r="{r}" fill="#04060c" stroke="{P["a1"]}" stroke-opacity="0.55"/><path d="{lit}" fill="#bfeee0" opacity="0.8"{flip}/></g>')

# ---------- optional live stats ----------
def gh(path):
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    h = {"User-Agent": "shadow-feed"}
    if tok: h["Authorization"] = "Bearer " + tok
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=h), timeout=10) as r:
        return json.load(r)
try:
    u = gh(f"/users/{OWNER}")
    REPOS, FOLLOWERS = u.get("public_repos"), u.get("followers")
except Exception:
    REPOS = FOLLOWERS = None

DEFS = f'''<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["bg"][0]}"/><stop offset="0.55" stop-color="{P["bg"][1]}"/><stop offset="1" stop-color="{P["bg"][2]}"/></linearGradient>
<radialGradient id="vig" cx="0.5" cy="0.5" r="0.75"><stop offset="0.5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.85"/></radialGradient>
<radialGradient id="mglow"><stop offset="0" stop-color="#bfeee0" stop-opacity="0.25"/><stop offset="1" stop-color="#bfeee0" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{P["a2"]}" stroke-opacity="0.12"/></pattern>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity="0.35"/></pattern>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'''

def backdrop(W, H):
    return f'<rect width="{W}" height="{H}" fill="url(#bg)"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'

def overlay(W, H):
    return f'<rect width="{W}" height="{H}" fill="url(#scan)"/><rect width="{W}" height="{H}" fill="url(#vig)"/>'

# ---------- spider web + network (shared) ----------
def web(cx, cy, a0, a1, R, spokes=9, rings=9, op=0.35):
    out = ""
    angs = [a0 + (a1 - a0) * i / (spokes - 1) for i in range(spokes)]
    for a in angs:
        out += f'<line x1="{cx}" y1="{cy}" x2="{cx+R*math.cos(math.radians(a)):.0f}" y2="{cy+R*math.sin(math.radians(a)):.0f}"/>'
    for k in range(1, rings + 1):
        r = R * k / rings
        pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in angs]
        d = f"M{pts[0][0]:.0f} {pts[0][1]:.0f}"
        for i in range(1, len(pts)):
            mx, my = (pts[i-1][0] + pts[i][0]) / 2, (pts[i-1][1] + pts[i][1]) / 2
            d += f" Q{cx+(mx-cx)*0.86:.0f} {cy+(my-cy)*0.86:.0f} {pts[i][0]:.0f} {pts[i][1]:.0f}"
        out += f'<path d="{d}" fill="none"/>'
    return f'<g stroke="{P["a2"]}" stroke-opacity="{op}" stroke-width="1">{out}</g>'

def network(W, H, n, avoid, sd, packets=14, maxd=170):
    r = random.Random(sd)
    pts, tries = [], 0
    while len(pts) < n and tries < 4000:
        tries += 1
        x, y = r.randint(15, W - 15), r.randint(15, H - 15)
        if any(a[0] <= x <= a[2] and a[1] <= y <= a[3] for a in avoid): continue
        if any((x - px) ** 2 + (y - py) ** 2 < 55 ** 2 for px, py in pts): continue
        pts.append((x, y))
    edges = set()
    for i, (x, y) in enumerate(pts):
        near = sorted(((x - px) ** 2 + (y - py) ** 2, j) for j, (px, py) in enumerate(pts) if j != i)
        for d2, j in near[:r.randint(2, 3)]:
            if d2 ** 0.5 <= maxd: edges.add((min(i, j), max(i, j)))
    el = list(edges)
    out = f'<g stroke="{P["a1"]}" stroke-width="1" stroke-opacity="0.3">' + "".join(
        f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}"><animate attributeName="stroke-opacity" values="0.12;0.5;0.12" dur="{r.uniform(2.5,6):.1f}s" begin="{r.uniform(0,4):.1f}s" repeatCount="indefinite"/></line>' for a, b in el) + "</g>"
    for i, (x, y) in enumerate(pts):
        out += f'<circle cx="{x}" cy="{y}" r="{r.choice([2,2.5,3,3.5])}" fill="{P["a3"] if i%9==0 else P["a1"]}" filter="url(#glow)"><animate attributeName="opacity" values="0.3;1;0.3" dur="{r.uniform(1.5,4):.1f}s" begin="{r.uniform(0,3):.1f}s" repeatCount="indefinite"/></circle>'
    r.shuffle(el)
    for a, b in el[:packets]:
        if r.random() < 0.5: a, b = b, a
        out += f'<circle r="2.6" fill="{r.choice([P["a1"], P["a1"], P["a3"], "#ffffff"])}" filter="url(#glow)"><animateMotion dur="{r.uniform(1.6,4):.1f}s" begin="{r.uniform(0,5):.1f}s" repeatCount="indefinite" path="M{pts[a][0]} {pts[a][1]} L{pts[b][0]} {pts[b][1]}"/></circle>'
    return out

# ---------- hero scenes (1000 x 360) ----------
HOOD = "M512 150 C352 150 272 300 282 470 C288 570 330 655 385 712 C440 748 584 748 639 712 C694 655 736 570 742 470 C752 300 672 150 512 150 Z"
FACE = "M512 290 C424 290 388 375 392 470 C397 565 435 628 512 648 C589 628 627 565 632 470 C636 375 600 290 512 290 Z"

def hooded(cx, base_y, s):
    return f'''<g transform="translate({cx - 512*s:.1f} {base_y - 735*s:.1f}) scale({s})">
<path d="M70 1300 C90 830 250 745 512 735 C774 745 934 830 954 1300 Z" fill="#05060c" stroke="{P["a1"]}" stroke-opacity="0.7" stroke-width="{3/s:.1f}"/>
<path d="{HOOD}" fill="#07080f" stroke="{P["a1"]}" stroke-opacity="0.9" stroke-width="{3.5/s:.1f}" filter="url(#glow)"/><path d="{HOOD}" fill="#07080f"/>
<path d="{FACE}" fill="#000" stroke="{P["a1"]}" stroke-opacity="0.45" stroke-width="{2/s:.1f}"/>
<text x="512" y="498" text-anchor="middle" font-family="{MONO}" font-size="74" font-weight="bold" fill="{P["a1"]}" filter="url(#glow)">&gt;_<animate attributeName="opacity" values="1;1;0.3;1" dur="2.4s" repeatCount="indefinite"/></text></g>'''

def scene_matrix(W, H):
    r = random.Random(seed(1))
    chars = "01<>/{}[]#$%&*=+ABCDEF"
    out = ""
    for x in range(430, 1000, 21):
        n, dur = r.randint(9, 15), r.uniform(5, 11)
        sp = "".join(f'<tspan x="{x}" dy="16" fill="{"#ffffff" if i == n-1 else P["a1"]}" fill-opacity="{0.12 + 0.78*(i/(n-1))**1.6:.2f}">{xesc(r.choice(chars))}</tspan>' for i in range(n))
        out += f'<g opacity="0.8"><animateTransform attributeName="transform" type="translate" from="0 {-n*16 - 10}" to="0 {H + 10}" dur="{dur:.1f}s" begin="-{r.uniform(0, dur):.1f}s" repeatCount="indefinite"/><text font-family="{MONO}" font-size="14">{sp}</text></g>'
    return out + hooded(770, 345, 0.36)

def scene_radar(W, H):
    r = random.Random(seed(2))
    cx, cy, R = 770, 180, 150
    out = ""
    for k in (1, 2, 3, 4):
        out += f'<circle cx="{cx}" cy="{cy}" r="{R*k/4}" fill="none" stroke="{P["a1"]}" stroke-opacity="0.3"/>'
    out += f'<line x1="{cx-R}" y1="{cy}" x2="{cx+R}" y2="{cy}" stroke="{P["a1"]}" stroke-opacity="0.25"/><line x1="{cx}" y1="{cy-R}" x2="{cx}" y2="{cy+R}" stroke="{P["a1"]}" stroke-opacity="0.25"/>'
    for a in range(0, 360, 10):
        x1, y1 = cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))
        x2, y2 = cx + (R - 6) * math.cos(math.radians(a)), cy + (R - 6) * math.sin(math.radians(a))
        out += f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{P["a1"]}" stroke-opacity="0.45"/>'
    sweep = f'M{cx} {cy} L{cx+R} {cy} A{R} {R} 0 0 0 {cx+R*math.cos(math.radians(-55)):.0f} {cy+R*math.sin(math.radians(-55)):.0f} Z'
    out += f'<defs><linearGradient id="sw" gradientUnits="userSpaceOnUse" x1="{cx+R}" y1="{cy}" x2="{cx+R*0.55}" y2="{cy-R*0.8}"><stop offset="0" stop-color="{P["a1"]}" stop-opacity="0.65"/><stop offset="1" stop-color="{P["a1"]}" stop-opacity="0"/></linearGradient></defs>'
    out += f'<g><animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="7s" repeatCount="indefinite"/><path d="{sweep}" fill="url(#sw)"/><line x1="{cx}" y1="{cy}" x2="{cx+R}" y2="{cy}" stroke="{P["a1"]}" stroke-width="2" filter="url(#glow)"/></g>'
    names = ["Java", "PHP", "React", "Next", "Python", "Spring", "Docker", "Cisco", "Figma", "Arduino", "SQL", "VPN"]
    r.shuffle(names)
    for i, nm in enumerate(names):
        ang, rad = r.uniform(0, 2 * math.pi), r.uniform(0.25, 0.92) * R
        x, y = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        col = P["a3"] if i % 5 == 0 else P["a1"]
        out += (f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.5" fill="{col}" filter="url(#glow)"><animate attributeName="opacity" values="1;0.15;1" dur="7s" begin="{(ang/(2*math.pi))*7:.2f}s" repeatCount="indefinite"/></circle>'
                f'<text x="{x+7:.0f}" y="{y+3:.0f}" font-family="{MONO}" font-size="10" fill="{col}" opacity="0.8">{nm}</text>')
    out += f'<circle cx="{cx}" cy="{cy}" r="4" fill="#fff" filter="url(#glow)"/>'
    return out

def scene_web(W, H):
    return (web(0, 0, 2, 88, 470) + web(W, 0, 92, 178, 470) + web(0, H, -88, -2, 280, 7, 7) + web(W, H, 182, 268, 280, 7, 7)
            + network(W, H, 46, [(40, 70, 640, 275)], seed(3), 16))

def scene_blackout(W, H):
    r = random.Random(seed(4))
    out, x = "", -10
    lit = 0.35 if PHASE in ("night", "dusk") else 0.14
    top_b = (0, 999, 0)
    while x < W:
        w = r.randint(26, 60)
        h = r.randint(26, 40) if x < 620 else r.randint(60, 205)
        top = H - h
        out += f'<rect x="{x}" y="{top}" width="{w}" height="{h}" fill="#03040a" stroke="{P["a1"]}" stroke-opacity="0.22"/>'
        for wy in range(top + 8, H - 6, 12):
            for wx in range(x + 6, x + w - 8, 10):
                if r.random() < lit:
                    c = r.choice([P["a1"], P["a1"], P["a2"], P["a3"]])
                    an = f'<animate attributeName="opacity" values="1;1;0.1;1" dur="{r.uniform(5,16):.0f}s" begin="{r.uniform(0,9):.0f}s" repeatCount="indefinite"/>' if r.random() < 0.18 else ""
                    out += f'<rect x="{wx}" y="{wy}" width="4" height="6" fill="{c}" opacity="0.85">{an}</rect>'
        if top < top_b[1]: top_b = (x + w / 2, top, h)
        x += w + r.randint(0, 6)
    ax, ay, _ = top_b
    out += f'<line x1="{ax}" y1="{ay}" x2="{ax}" y2="{ay-28}" stroke="#666" stroke-width="1.5"/><circle cx="{ax}" cy="{ay-30}" r="3.2" fill="{P["a3"]}" filter="url(#glow)"><animate attributeName="opacity" values="1;0.1;1" dur="1.4s" repeatCount="indefinite"/></circle>'
    for i in range(46):  # rain
        rx, ry, ln = r.randint(0, W), r.randint(-60, H), r.randint(10, 22)
        d = r.uniform(0.7, 1.4)
        out += f'<line x1="0" y1="0" x2="-3" y2="{ln}" stroke="{P["a1"]}" stroke-opacity="0.28" transform="translate({rx} {ry})"><animateTransform attributeName="transform" type="translate" from="{rx} -30" to="{rx-30} {H+30}" dur="{d:.2f}s" begin="-{r.uniform(0,d):.2f}s" repeatCount="indefinite"/></line>'
    out += f'<rect y="{H-60}" width="{W}" height="60" fill="url(#fog)"/>'
    return out

SCENE_FN = dict(matrix=scene_matrix, radar=scene_radar, web=scene_web, blackout=scene_blackout)

LINES = ["Silent code. Loud results.", "Build in the dark. Ship in the light.", "Every system has a door. I build the ones that stay shut.",
         "Less noise. More signal.", "Small commits. Big shadows.", "Stay hidden. Stay shipping.", "Think like an attacker. Build like a guardian.",
         "Networks are just machines talking. I listen.", "Make it work. Make it secure. Make it beautiful.", "Power is quiet.",
         "They see the interface. I see the system.", "Trust nothing. Verify everything.", "The best exploit is a good design.", "No face. No name. Just work."]
LINE = LINES[YDAY % len(LINES)]
CIPHER = base64.b64encode(LINE.encode()).decode()

def hero():
    W, H = 1000, 360
    meta = [f"NODE TUNIS {now:%H:%M}", PHASE.upper(), f"THREAT {P['threat']}", f"SESSION {SESSION}", f"SCENE {SCENE.upper()}"]
    if REPOS is not None: meta.append(f"REPOS {REPOS}")
    gt = "0;0.8;0.84;0.88;0.92;1"
    def glitch(col, dx, dy):
        return (f'<text x="60" y="178" font-family="{MONO}" font-size="70" font-weight="bold" letter-spacing="6" fill="{col}" opacity="0">3ABCH9LEU'
                f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx} {dy};{-dx} {-dy};0 0;0 0" keyTimes="{gt}" dur="5s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;0;0.85;0.85;0;0" keyTimes="{gt}" dur="5s" repeatCount="indefinite"/></text>')
    moon = moon_glyph(905, 52, 12) if PHASE in ("night", "dawn", "dusk") else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>{DEFS}
<linearGradient id="fog" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["a2"]}" stop-opacity="0"/><stop offset="1" stop-color="{P["a2"]}" stop-opacity="0.3"/></linearGradient>
<linearGradient id="shade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity="0.78"/><stop offset="0.55" stop-color="#000" stop-opacity="0.35"/><stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient>
</defs>
{backdrop(W, H)}
{SCENE_FN[SCENE](W, H)}
{moon}
<rect width="{W}" height="{H}" fill="url(#shade)"/>
{overlay(W, H)}
<text x="62" y="86" font-family="{MONO}" font-size="13" letter-spacing="5" fill="{P["a3"]}">[ IDENTITY: REDACTED ]<animate attributeName="opacity" values="1;0.25;1;1;0.6;1" dur="3.2s" repeatCount="indefinite"/></text>
{glitch(P["a2"], -5, 0)}{glitch(P["a3"], 5, 2)}
<text x="60" y="178" font-family="{MONO}" font-size="70" font-weight="bold" letter-spacing="6" fill="{P["a1"]}" filter="url(#glow)">3ABCH9LEU</text>
<text x="62" y="214" font-family="{MONO}" font-size="16" letter-spacing="3" fill="{P["txt"]}" opacity="0.9">Full-Stack  ·  AI  ·  Networks  ·  Cybersecurity</text>
<text x="62" y="248" font-family="{MONO}" font-size="15" fill="{P["a2"]}">&gt; {LINE}<tspan fill="{P["a1"]}"><animate attributeName="opacity" values="1;0;1" dur="0.9s" repeatCount="indefinite"/>_</tspan></text>
<text x="62" y="274" font-family="{MONO}" font-size="10" letter-spacing="1" fill="{P["a1"]}" opacity="0.5">ENCRYPTED: {CIPHER}</text>
<circle cx="66" cy="318" r="4" fill="{P["a1"]}" filter="url(#glow)"><animate attributeName="opacity" values="1;0.2;1" dur="1.4s" repeatCount="indefinite"/></circle>
<text x="80" y="322" font-family="{MONO}" font-size="11" letter-spacing="2" fill="{P["txt"]}" opacity="0.9">{"  ·  ".join(meta)}</text>
</svg>'''

def heading(title, idx):
    r = random.Random(seed(20 + idx))
    xs = [560] + sorted(r.sample(range(590, 860, 28), 5)) + [890]
    ys = [r.choice([34, 40, 46, 52]) for _ in xs]
    path = "M" + " L".join(f"{x} {y}" for x, y in zip(xs, ys))
    nodes = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="{P["a1"]}" filter="url(#glow)"><animate attributeName="opacity" values="0.3;1;0.3" dur="{r.uniform(1.5,3):.1f}s" begin="{r.uniform(0,2):.1f}s" repeatCount="indefinite"/></circle>' for x, y in zip(xs, ys))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 76" width="900" height="76">
<defs>{DEFS}</defs>
<rect width="900" height="76" rx="10" fill="#03050a" stroke="{P["a1"]}" stroke-opacity="0.35"/><rect width="900" height="76" rx="10" fill="url(#grid)"/>
<text x="20" y="46" font-family="{MONO}" font-size="26" font-weight="bold" letter-spacing="3" fill="{P["txt"]}"><tspan fill="{P["a1"]}">anon@3abch9leu:~$ </tspan>{title}<tspan fill="{P["a1"]}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/>_</tspan></text>
<text x="884" y="16" text-anchor="end" font-family="{MONO}" font-size="11" fill="{P["a2"]}" letter-spacing="3">[ NODE {idx:02d} ]</text>
<path d="{path}" fill="none" stroke="{P["a2"]}" stroke-opacity="0.6" stroke-width="1.5"/>{nodes}
<circle r="3.4" fill="{P["a3"]}" filter="url(#glow)"><animateMotion dur="3.4s" repeatCount="indefinite" path="{path}"/></circle>
</svg>'''

def divider(variant):
    r = random.Random(seed(40 + variant))
    W, H = 900, 70
    if variant == 0:
        body = web(0, 0, 4, 86, 100, 6, 5) + web(W, H, 184, 266, 100, 6, 5) + network(W, H, 16, [(380, 0, 520, 70)], seed(41), 8, 150)
    else:
        xs = list(range(40, 861, 40))
        pts = [(x, 35 + r.randint(-20, 20)) for x in xs if not 385 < x < 515]
        body = "".join(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{P["a1"]}" stroke-opacity="0.4"/>' for a, b in zip(pts, pts[1:]) if abs(a[0] - b[0]) < 60)
        body += "".join(f'<circle cx="{x}" cy="{y}" r="{r.choice([2,2.6,3.2])}" fill="{P["a1"]}" filter="url(#glow)"><animate attributeName="opacity" values="1;0.2;1" dur="{r.uniform(1.6,4):.1f}s" begin="{r.uniform(0,3):.1f}s" repeatCount="indefinite"/></circle>' for x, y in pts)
        body += f'<circle r="3" fill="{P["a3"]}" filter="url(#glow)"><animateMotion dur="5s" repeatCount="indefinite" path="M40 35 L860 35"/></circle>'
    lock = f'''<g transform="translate(450 35)" filter="url(#glow)" fill="none" stroke="{P["a1"]}" stroke-width="2.4" stroke-linecap="round"><rect x="-11" y="-3" width="22" height="16" rx="3" fill="#020308"/><path d="M-6 -3 V-8 C-6 -17 6 -17 6 -8 V-3"/><circle cy="5" r="1.8" fill="{P["a1"]}" stroke="none"/></g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>{DEFS}</defs><rect width="{W}" height="{H}" rx="10" fill="#03050a"/>{body}<circle cx="450" cy="35" r="19" fill="#03050a" stroke="{P["a1"]}" stroke-opacity="0.5"/>{lock}
</svg>'''

CLOSERS = dict(night="Silence is the loudest signal.", dawn="System rebooting. New cycle.", day="Hidden in plain sight.", dusk="Going dark.")
def footer():
    W, H = 1000, 200
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<defs>{DEFS}</defs>
{backdrop(W, H)}{web(0, H, -88, -2, 320, 8, 8)}{web(W, H, 182, 268, 320, 8, 8)}{network(W, H, 26, [(230, 50, 770, 160)], seed(51), 12, 150)}
{overlay(W, H)}
<text x="500" y="88" text-anchor="middle" font-family="{MONO}" font-size="26" font-weight="bold" letter-spacing="3" fill="{P["a1"]}" filter="url(#glow)">{CLOSERS[PHASE]}<animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite"/></text>
<text x="500" y="122" text-anchor="middle" font-family="{MONO}" font-size="12" letter-spacing="5" fill="{P["a3"]}">[ CONNECTION CLOSED  ·  TRACE: NONE ]</text>
<text x="500" y="146" text-anchor="middle" font-family="{MONO}" font-size="11" letter-spacing="3" fill="{P["txt"]}" opacity="0.65">LAST SYNC {now:%Y-%m-%d %H:%M}  ·  {PHASE.upper()}  ·  SESSION {SESSION}</text>
</svg>'''

os.makedirs(OUT, exist_ok=True)
files = {"hero.svg": hero(), "footer.svg": footer(), "divider-a.svg": divider(0), "divider-b.svg": divider(1)}
for i, t in enumerate(["WHOAMI", "ARSENAL", "PROJECTS", "LOGS", "STATUS", "CONTACT"], 1):
    files[f"h-{t.lower()}.svg"] = heading(t, i)
for name, content in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(content)
print(f"[shadow-feed] {now:%Y-%m-%d %H:%M} Tunis | phase={PHASE} | scene={SCENE} | session={SESSION} | moon={MOON_PCT}% | repos={REPOS} | {len(files)} files -> {OUT}/")

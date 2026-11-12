"""Builds the profile README art (assets/*.svg) in Domi's personal brand.

Brand tokens come from domirosario.com: warm near-black, ink, muted greys, one
coral "pen" accent used only for hand-drawn strokes, Newsreader for display,
Inter for small text, everything lowercase. Text is converted to outlines so
GitHub renders the real typefaces (an <img> SVG can't load web fonts).

Every asset is built twice (dark + light) and switched with <picture> in the
README. Only the coral pen strokes animate (they draw themselves in, like on
domirosario.com); text is always static so nothing depends on animation.

Run:  uv run --with fonttools --with brotli --with uharfbuzz python scripts/build.py
"""
from __future__ import annotations

import io
import pathlib
import textwrap

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"
W = 880

THEMES = {
    "dark": dict(bg="#100f0d", ink="#f2ede4", muted="#a8a296", faint="#8a8478",
                 rule="rgba(242,237,228,.13)", coral="#ee6a4a", grain="screen", grain_op=".07"),
    "light": dict(bg="#f2ede4", ink="#14120f", muted="#625d54", faint="#7d776c",
                  rule="rgba(20,18,15,.14)", coral="#e2583a", grain="multiply", grain_op=".09"),
}

# ---------------------------------------------------------------- type → paths
_cache: dict = {}


def _font(name: str, **axes):
    key = (name, tuple(sorted(axes.items())))
    if key not in _cache:
        tt = TTFont(FONTS / f"{name}.woff2")
        tt = instantiateVariableFont(tt, axes)
        tt.flavor = None
        buf = io.BytesIO(); tt.save(buf)
        hbfont = hb.Font(hb.Face(hb.Blob(buf.getvalue())))
        _cache[key] = (tt, hbfont, tt["head"].unitsPerEm)
    return _cache[key]


FACES = {
    "display": ("newsreader", dict(wght=400, opsz=72)),
    "display-it": ("newsreader-italic", dict(wght=400, opsz=72)),
    "serif": ("newsreader", dict(wght=420, opsz=20)),
    "serif-it": ("newsreader-italic", dict(wght=400, opsz=20)),
    "sans": ("inter", dict(wght=430)),
    "sans-med": ("inter", dict(wght=520)),
}


def measure(face: str, s: str, size: float, track: float = 0) -> float:
    return text(face, s, size, 0, 0, track=track)[1]


def text(face: str, s: str, size: float, x: float, y: float, track: float = 0,
         anchor: str = "start") -> tuple[str, float]:
    """Outline `s` at baseline (x, y). Returns (path data, advance width)."""
    name, axes = FACES[face]
    tt, hbfont, upem = _font(name, **axes)
    buf = hb.Buffer(); buf.add_str(s); buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    scale = size / upem
    order = tt.getGlyphOrder()
    gs = tt.getGlyphSet()
    width = sum(p.x_advance for p in buf.glyph_positions) * scale + track * size * max(len(s) - 1, 0)
    if anchor == "middle":
        x -= width / 2
    elif anchor == "end":
        x -= width
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    cx = x
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        g = gs[order[info.codepoint]]
        g.draw(TransformPen(pen, (scale, 0, 0, -scale, cx + pos.x_offset * scale, y - pos.y_offset * scale)))
        cx += pos.x_advance * scale + track * size
    return pen.getCommands(), width


def t(face, s, size, x, y, cls, track: float = 0, anchor="start", extra=""):
    d, w = text(face, s, size, x, y, track, anchor)
    return f'<path class="{cls}" d="{d}"{extra}/>', w


# ---------------------------------------------------------------- shared bits
MARK = ("M44.2 12.6C33.1 7.9 19.2 12.9 14.1 24C9 35.2 13.9 48 24.6 52.6"
        "C35.3 57.2 47.8 52.4 52.4 41.9C55.6 34.7 54.4 26.8 50 21")
MARK_TAIL = "M44.2 12.6C41.9 11.4 39.3 10.7 36.6 10.6"
UNDERLINE = "M3 8.6C40 4.1 92 3.2 140 5.4c22 1 40 2.6 57 4.6"  # viewBox 200×12
ARROW = "M2 7.7c7-.9 14-1.1 23-.5M19.2 2.1l5.9 5.1-6 5"  # viewBox 28×14

GRAIN = ("<filter id='g' x='0' y='0' width='100%' height='100%'><feTurbulence type='fractalNoise' "
         "baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  "
         "0 0 0 0 1  0 0 0 1.5 -.4'/></filter>")
GRAIN_LIGHT = GRAIN.replace("0 0 0 0 1  0 0 0 0 1  0 0 0 0 1", "0 0 0 0 0  0 0 0 0 0  0 0 0 0 0")


def style(th: dict, extra: str = "") -> str:
    return f"""<style>
.ink{{fill:{th['ink']}}}.mute{{fill:{th['muted']}}}.faint{{fill:{th['faint']}}}
.rule{{stroke:{th['rule']};stroke-width:1}}
.pen{{fill:none;stroke:{th['coral']};stroke-linecap:round;stroke-linejoin:round}}
.line{{fill:none;stroke:{th['faint']};stroke-linecap:round}}
.draw{{stroke-dasharray:1;animation:draw 1.5s cubic-bezier(.6,0,.3,1) both}}
.rise{{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}}
@keyframes draw{{from{{stroke-dashoffset:1}}to{{stroke-dashoffset:0}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
{extra}
@media (prefers-reduced-motion:reduce){{.draw,.rise{{animation:none}}}}
</style>"""


def svg(w, h, title, desc, body, th, extra_css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{title}</title><desc id="d">{desc}</desc>'
            f'{style(th, extra_css)}{body}</svg>\n')


def delay(s: float) -> str:
    return f' style="animation-delay:{s:.2f}s"'


# ---------------------------------------------------------------- hero
def hero(th, mode):
    h = 340
    p = []
    grain = GRAIN if mode == "dark" else GRAIN_LIGHT
    p.append(f'<defs>{grain}<clipPath id="c"><rect width="{W}" height="{h}" rx="18"/></clipPath></defs>')
    p.append(f'<g clip-path="url(#c)"><rect width="{W}" height="{h}" fill="{th["bg"]}"/>'
             f'<rect width="{W}" height="{h}" filter="url(#g)" opacity="{th["grain_op"]}" '
             f'style="mix-blend-mode:{th["grain"]}"/></g>')
    # top strip
    p.append(t("sans-med", "domi rosario", 12.5, 44, 50, "mute", track=.06, extra=delay(.1))[0])
    p.append(t("sans", "@frmdomi", 12.5, W - 44, 50, "faint", track=.04, anchor="end", extra=delay(.1))[0])
    # mark
    mx, my, ms = 44, 112, 128 / 64
    p.append(f'<g transform="translate({mx} {my}) scale({ms})">'
             f'<path class="pen draw" d="{MARK}" stroke-width="7" pathLength="1"{delay(.35)}/>'
             f'<path class="pen draw" d="{MARK_TAIL}" stroke-width="5" pathLength="1" opacity=".9" '
             f'style="animation-delay:1.55s;animation-duration:.5s"/></g>')
    # headline
    x = 212
    p.append(t("display", "indie game dev,", 64, x, 172, "ink", track=-.022, extra=delay(.55))[0])
    p.append(t("display", "going full-time.", 64, x, 240, "mute", track=-.022, extra=delay(.8))[0])
    # footer line
    p.append(f'<line class="rule" x1="44" y1="286.5" x2="{W-44}" y2="286.5"/>')
    p.append(t("sans", "i make apps and small games, and post about it.", 13.5, 44, 313, "mute",
               track=.005, extra=delay(1.1))[0])
    p.append(t("serif-it", "trying to make this my life.", 16, W - 44, 313, "ink", anchor="end",
               extra=delay(1.25))[0])
    return svg(W, h, "domi rosario: indie game dev, going full-time.",
               "I make apps and small games, and post about it. Trying to make this my life.", "".join(p), th)


# ---------------------------------------------------------------- section heads
def head(th, mode, title, note, ident):
    h = 74
    p = []
    tp, tw = t("display", title, 40, 0, 46, "ink", track=-.02)
    p.append(tp)
    p.append(t("sans", note, 12.5, W, 44, "faint", track=.04, anchor="end")[0])
    # pen underline under the title
    p.append(f'<svg x="-2" y="52" width="{tw + 8:.0f}" height="12" viewBox="0 0 200 12" preserveAspectRatio="none">'
             f'<path class="pen draw" d="{UNDERLINE}" stroke-width="2.4" pathLength="1" '
             f'vector-effect="non-scaling-stroke"{delay(.3)}/></svg>')
    p.append(f'<line class="rule" x1="0" y1="{h-.5}" x2="{W}" y2="{h-.5}"/>')
    return svg(W, h, title, note, "".join(p), th)


# ---------------------------------------------------------------- project rows
ROWS = [
    ("making-games", "01", "games",
     ["small browser games, trying to get the first one",
      "into full launch. and starting my first roblox game."],
     "in the works"),
    ("euromakers", "02", "euromakers",
     ["the home of european software. a curated directory",
      "of products made in europe, with weekly launches."],
     "euromakers.org"),
    ("whatsmyusage", "03", "whatsmyusage",
     ["a mac menu-bar app that shows how much of your ai",
      "limits you've used, before you run into them."],
     "getwhatsmyusage.com"),
    ("otlet", "04", "otlet",
     ["turns every new tab into a search box for",
      "everything you've saved."],
     "otlet.page"),
]


def row(th, mode, key, num, name, lines, link, focus=False):
    h = 112
    p = []
    p.append(t("sans-med", num, 11.5, 0, 50, "faint", track=.08)[0])
    np, nw = t("display", name, 36, 44, 56, "ink", track=-.02)
    p.append(np)
    if focus:
        p.append(f'<svg x="40" y="62" width="{nw + 8:.0f}" height="12" viewBox="0 0 200 12" '
                 f'preserveAspectRatio="none"><path class="pen draw" d="{UNDERLINE}" stroke-width="2.4" '
                 f'pathLength="1" vector-effect="non-scaling-stroke"{delay(.5)}/></svg>')
    for i, ln in enumerate(lines):
        p.append(t("sans", ln, 14.5, 360, 42 + i * 23, "mute", track=.002)[0])
    is_link = "." in link
    lp, lw = t("sans-med", link, 12.5, 360, 92, "ink" if is_link else "faint", track=.03)
    p.append(lp)
    if is_link:
        p.append(f'<svg x="{360 + lw + 7:.1f}" y="83" width="17" height="9" viewBox="0 0 28 14">'
                 f'<path class="pen" d="{ARROW}" stroke-width="2.2"/></svg>')
    p.append(f'<line class="rule" x1="0" y1="{h-.5}" x2="{W}" y2="{h-.5}"/>')
    return svg(W, h, f"{name}: {link}", " ".join(lines), "".join(p), th)


# ---------------------------------------------------------------- the arc
STOPS = [
    ("2024", ["b.sc. done,", "first degree"]),
    ("2025", ["started", "euromakers"]),
    ("2026", ["built saas", "and small tools"]),
    ("oct 2026", ["switched focus", "to games"]),
    ("nov 2026", ["m.sc. done,", "all degrees"]),
    ("next", ["full-time game dev,", "making content."]),
]


def arc(th, mode):
    h = 230
    p = []
    tp, tw = t("display", "the arc.", 40, 0, 46, "ink", track=-.02)
    p.append(tp)
    p.append(t("sans", "you're early enough to watch all of it", 12.5, W, 44, "faint", track=.04, anchor="end")[0])
    p.append(f'<svg x="-2" y="52" width="{tw + 8:.0f}" height="12" viewBox="0 0 200 12" preserveAspectRatio="none">'
             f'<path class="pen draw" d="{UNDERLINE}" stroke-width="2.4" pathLength="1" '
             f'vector-effect="non-scaling-stroke"{delay(.3)}/></svg>')
    ly = 140
    x0 = 8
    lastw = max(measure('serif-it', ln, 18) for ln in STOPS[-1][1])
    step = (W - x0 - lastw) / (len(STOPS) - 1)
    xs = [x0 + i * step for i in range(len(STOPS))]
    last = xs[-1]
    # hand-drawn line: gentle wobble between stops, ending inside the final mark
    wob = [0, -2.2, 1.6, -1.4, 2.0, -1.0]
    d = f"M{xs[0]} {ly + wob[0]}"
    for i in range(1, len(xs)):
        xa, xb = xs[i - 1], xs[i] if i < len(xs) - 1 else last - 14
        d += f" C{xa + step*.4:.1f} {ly + wob[i-1] + 3:.1f} {xb - step*.4:.1f} {ly + wob[i] - 3:.1f} {xb:.1f} {ly + wob[i]:.1f}"
    p.append(f'<path class="line draw" d="{d}" stroke-width="1.5" pathLength="1" '
             f'style="animation-delay:.4s;animation-duration:2.2s"/>')
    for i, (year, lines) in enumerate(STOPS):
        x = xs[i]
        dl = .4 + 2.2 * i / (len(STOPS) - 1)
        p.append(t("sans-med", year, 11.5, x, ly - 22, "faint", track=.07, extra=delay(dl))[0])
        cls = "ink" if i == len(STOPS) - 1 else "ink"
        for j, ln in enumerate(lines):
            p.append(t("serif" if i < len(STOPS) - 1 else "serif-it", ln, 18, x, ly + 36 + j * 23,
                       ("mute" if j else f"{cls}"), extra=delay(dl + .1))[0])
        if i < len(STOPS) - 1:
            p.append(f'<circle cx="{x}" cy="{ly + wob[i]}" r="3.6" fill="{th["ink"]}" />')
        else:
            s = 30 / 64
            p.append(f'<g transform="translate({x - 15 + 6} {ly - 15}) scale({s})">'
                     f'<path class="pen draw" d="{MARK}" stroke-width="7" pathLength="1"{delay(dl)}/>'
                     f'<path class="pen draw" d="{MARK_TAIL}" stroke-width="5" pathLength="1" '
                     f'style="animation-delay:{dl + .9:.2f}s;animation-duration:.4s"/></g>')
    desc = "; ".join(f"{y}: {' '.join(l)}" for y, l in STOPS)
    return svg(W, h, "the arc", desc, "".join(p), th)


# ---------------------------------------------------------------- link chips
LINKS = [("x", "x"), ("youtube", "youtube"), ("tiktok", "tiktok"), ("instagram", "instagram"),
         ("site", "domirosario.com")]


def chip(th, mode, label):
    lp, lw = t("serif", label, 19, 0, 22, "ink")
    w = lw + 24
    body = lp + (f'<svg x="{lw + 5:.1f}" y="10" width="19" height="10" viewBox="0 0 28 14">'
                 f'<path class="pen" d="{ARROW}" stroke-width="2.2"/></svg>')
    return svg(round(w), 30, label, f"{label} link", body, th)


def main():
    OUT.mkdir(exist_ok=True)
    built = []
    for mode, th in THEMES.items():
        files = {
            f"hero-{mode}.svg": hero(th, mode),
            f"now-{mode}.svg": head(th, mode, "now.", "what i'm working on", "now"),
            f"journey-{mode}.svg": arc(th, mode),
        }
        for i, (key, num, name, lines, link) in enumerate(ROWS):
            files[f"row-{key}-{mode}.svg"] = row(th, mode, key, num, name, lines, link, focus=(i == 0))
        for key, label in LINKS:
            files[f"link-{key}-{mode}.svg"] = chip(th, mode, label)
        for name, content in files.items():
            (OUT / name).write_text(content)
            built.append((name, len(content)))
    for n, s in built:
        print(f"{s/1024:6.1f} KB  {n}")


if __name__ == "__main__":
    main()

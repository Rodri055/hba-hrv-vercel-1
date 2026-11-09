"""
HANNA · hba_report/draw.py
Primitivas de dibujo vectorial (reportlab) para el informe: paleta, tipografía, íconos y gráficos.
Todo es vectorial: se ve nítido al imprimir y al hacer zoom, y no depende de matplotlib.
"""
import math
import os
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

# ── paleta ──────────────────────────────────────────────────────────────────────────────────────────────────
WHITE = HexColor("#FFFFFF")
INK, DEEP, HANNA, ELECTRIC = HexColor("#0A1F4D"), HexColor("#0A2A6B"), HexColor("#0A5CFF"), HexColor("#1F8BFF")
MID, CELESTE, SKY, ICE = HexColor("#5AA9FF"), HexColor("#A9D4FF"), HexColor("#DCEBFF"), HexColor("#F1F7FF")
INK2, INK3, LINE = HexColor("#3F5C94"), HexColor("#5A74A3"), HexColor("#D3E3FB")
GREEN, GREEN_T, GREEN_D = HexColor("#16A34A"), HexColor("#E7F7ED"), HexColor("#0B6B33")
AMBER, AMBER_T, AMBER_D = HexColor("#F59E0B"), HexColor("#FEF3D6"), HexColor("#92520A")
RED, RED_T, RED_D = HexColor("#DC2626"), HexColor("#FDE8E8"), HexColor("#A61B1B")
CYAN, CYAN_T, CYAN_D = HexColor("#3FA0FF"), HexColor("#E4F1FF"), HexColor("#0B4FA8")

# estado → (color sólido, fondo tenue, texto)
TONE = {"green": (GREEN, GREEN_T, GREEN_D), "amber": (AMBER, AMBER_T, AMBER_D), "red": (RED, RED_T, RED_D),
        "cyan": (CYAN, CYAN_T, CYAN_D), "blue": (HANNA, SKY, DEEP)}

# ── tipografía ──────────────────────────────────────────────────────────────────────────────────────────────
_FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
F, FSB, FB, SSB, SB = "Fig", "Fig-SB", "Fig-B", "Sora-SB", "Sora-B"
_registered = False


def register_fonts():
    global _registered
    if _registered:
        return
    for name, file in [(F, "Figtree-Regular"), (FSB, "Figtree-SemiBold"), (FB, "Figtree-Bold"),
                       (SSB, "Sora-SemiBold"), (SB, "Sora-Bold")]:
        pdfmetrics.registerFont(TTFont(name, os.path.join(_FONTS, file + ".ttf")))
    registerFontFamily(F, normal=F, bold=FB, italic=F, boldItalic=FB)
    _registered = True


WARNINGS = []  # textos que no entraron en su marco (los tests exigen que quede vacío)


def tw(s, font, size):
    return pdfmetrics.stringWidth(s, font, size)


def fit_text(s, font, size, max_w):
    """Acorta con puntos suspensivos si no entra en una línea."""
    if tw(s, font, size) <= max_w:
        return s
    while s and tw(s + "…", font, size) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def text(c, s, x, y, font=F, size=9, color=INK, align="l", max_w=None):
    if max_w:
        s = fit_text(s, font, size, max_w)
    c.setFont(font, size)
    c.setFillColor(color)
    {"l": c.drawString, "r": c.drawRightString, "c": c.drawCentredString}[align](x, y, s)


def para(c, s, x, y_top, w, font=F, size=9, color=INK, leading=None, max_h=None, min_size=6.6, markup=False, align=TA_LEFT):
    """Párrafo ajustado a un marco. Reduce la letra y, en último caso, recorta con '…' (registrando el aviso)."""
    body = s if markup else escape(s)
    sz = size
    while True:
        st = ParagraphStyle("p", fontName=font, fontSize=sz, leading=leading or sz * 1.32, textColor=color, alignment=align)
        p = Paragraph(body, st)
        _, h = p.wrap(w, 10000)
        if max_h is None or h <= max_h + 0.01:
            break
        if sz > min_size:
            sz = max(min_size, sz - 0.4)
            continue
        words = body.split(" ")
        while len(words) > 3 and h > max_h + 0.01:
            words.pop()
            p = Paragraph(" ".join(words).rstrip(" ,;:.") + "…", st)
            _, h = p.wrap(w, 10000)
        WARNINGS.append(("recortado", s[:60]))
        break
    p.drawOn(c, x, y_top - h)
    return h


def lines_height(s, w, font=F, size=9, leading=None):
    st = ParagraphStyle("p", fontName=font, fontSize=size, leading=leading or size * 1.32)
    return Paragraph(escape(s), st).wrap(w, 10000)[1]


# ── formas ──────────────────────────────────────────────────────────────────────────────────────────────────
def rrect(c, x, y, w, h, r=8, fill=None, stroke=None, lw=0.8, dash=None):
    c.saveState()
    if fill is not None:
        c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
    if dash:
        c.setDash(*dash)
    c.roundRect(x, y, w, h, r, stroke=1 if stroke is not None else 0, fill=1 if fill is not None else 0)
    c.restoreState()


def card(c, x, y, w, h, r=12, fill=WHITE, border=LINE):
    """Tarjeta con sombra suave."""
    c.saveState()
    for i, a in enumerate((0.035, 0.03, 0.025)):
        c.setFillColor(Color(0.04, 0.17, 0.42, alpha=a))
        c.roundRect(x - i * 0.6, y - 1.2 - i * 1.4, w + i * 1.2, h, r + i, stroke=0, fill=1)
    c.restoreState()
    rrect(c, x, y, w, h, r, fill=fill, stroke=border, lw=0.7)


def gradient_rect(c, x, y, w, h, colors, angle="diag", r=0):
    c.saveState()
    p = c.beginPath()
    if r:
        p.roundRect(x, y, w, h, r)
    else:
        p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    if angle == "diag":
        c.linearGradient(x, y + h, x + w, y, colors, extend=True)
    elif angle == "h":
        c.linearGradient(x, y, x + w, y, colors, extend=True)
    else:
        c.linearGradient(x, y + h, x, y, colors, extend=True)
    c.restoreState()


def chip(c, x, y, s, tone="blue", size=7.4, align="l", solid=False):
    """Etiqueta redondeada. y = línea base del texto. Devuelve el ancho."""
    fg, bg, tx = TONE[tone]
    w = tw(s, FB, size) + 12
    x0 = x if align == "l" else x - w
    rrect(c, x0, y - 3.4, w, size + 6.2, (size + 6.2) / 2, fill=fg if solid else bg)
    text(c, s, x0 + 6, y, FB, size, WHITE if solid else tx)
    return w


def dot(c, x, y, r, color):
    c.saveState()
    c.setFillColor(color)
    c.circle(x, y, r, stroke=0, fill=1)
    c.restoreState()


def fit_items(items, w, size, gap, max_h):
    """Devuelve los primeros ítems que caben en max_h (para no recortar texto)."""
    out, used = [], 0
    for it in items:
        h = lines_height(it, w - 11, F, size) + gap
        if used + h > max_h + gap and out:
            break
        out.append(it); used += h
    return out


def bullets(c, items, x, y_top, w, size=8.4, gap=3.2, tones=None, max_h=None, color=INK):
    """Lista con viñetas de color. Devuelve la altura usada."""
    y = y_top
    for i, it in enumerate(items):
        tone = (tones[i] if tones else "blue")
        h = para(c, it, x + 11, y, w - 11, F, size, color, max_h=(max_h - (y_top - y)) if max_h else None)
        dot(c, x + 3.2, y - size * 0.78, 2.3, TONE[tone][0])
        y -= h + gap
    return y_top - y


# ── íconos (cuadrícula 24x24, y hacia abajo, trazo redondeado) ────────────────────────────────────────────
def icon(c, name, x, y, size=14, color=DEEP, lw=2.0):
    """Dibuja el ícono con esquina inferior izquierda en (x, y)."""
    c.saveState()
    c.translate(x, y + size)
    c.scale(size / 24.0, -size / 24.0)
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(lw)
    c.setLineCap(1)
    c.setLineJoin(1)

    def poly(pts, close=False, fill=0):
        p = c.beginPath()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        if close:
            p.close()
        c.drawPath(p, stroke=1, fill=fill)

    def circ(cx, cy, r, fill=0):
        c.circle(cx, cy, r, stroke=0 if fill else 1, fill=fill)

    if name == "pulse":
        poly([(2, 12), (6.5, 12), (9, 4), (14, 20), (16.5, 12), (22, 12)])
    elif name == "heart":
        p = c.beginPath()
        p.moveTo(12, 21)
        p.curveTo(4, 14.5, 2, 11, 2, 8)
        p.curveTo(2, 5, 4.2, 3, 6.8, 3)
        p.curveTo(9, 3, 10.9, 4.2, 12, 6.2)
        p.curveTo(13.1, 4.2, 15, 3, 17.2, 3)
        p.curveTo(19.8, 3, 22, 5, 22, 8)
        p.curveTo(22, 11, 20, 14.5, 12, 21)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
    elif name == "moon":
        c.saveState()
        p = c.beginPath()
        p.circle(11, 13, 9)
        c.clipPath(p, stroke=0, fill=0)
        q = c.beginPath()
        q.rect(-2, -2, 30, 30)
        q.circle(16.5, 8.5, 7.4)
        c.drawPath(q, stroke=0, fill=1)
        c.restoreState()
    elif name == "run":  # tendencia ascendente
        poly([(2, 17), (9, 10), (13.5, 14.5), (22, 6)])
        poly([(16, 6), (22, 6), (22, 12)])
    elif name == "brain":  # círculos concéntricos (respiración / calma)
        circ(12, 12, 9.5)
        circ(12, 12, 5.2)
        circ(12, 12, 1.4, fill=1)
    elif name == "check":
        poly([(4, 12.5), (9.5, 18), (20.5, 6.5)])
    elif name == "drop":
        p = c.beginPath()
        p.moveTo(12, 2.5)
        p.curveTo(8, 8, 5, 11.5, 5, 15)
        p.curveTo(5, 19, 8.1, 22, 12, 22)
        p.curveTo(15.9, 22, 19, 19, 19, 15)
        p.curveTo(19, 11.5, 16, 8, 12, 2.5)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
    elif name == "calendar":
        c.roundRect(3, 5, 18, 16, 2.5, stroke=1, fill=0)
        poly([(3, 10), (21, 10)])
        poly([(8, 3), (8, 7)])
        poly([(16, 3), (16, 7)])
    elif name == "target":
        circ(12, 12, 9.5)
        circ(12, 12, 5.2)
        circ(12, 12, 1.4, fill=1)
    elif name == "alert":
        poly([(12, 3), (22, 20.5), (2, 20.5)], close=True)
        poly([(12, 9.5), (12, 14.5)])
        circ(12, 17.4, 1.1, fill=1)
    elif name == "info":
        circ(12, 12, 9.5)
        poly([(12, 11), (12, 16.5)])
        circ(12, 7.6, 1.1, fill=1)
    elif name == "clock":
        circ(12, 12, 9.5)
        poly([(12, 6.5), (12, 12), (15.8, 14.2)])
    elif name == "chart":
        poly([(5, 20), (5, 13)])
        poly([(12, 20), (12, 5)])
        poly([(19, 20), (19, 9)])
    elif name == "shield":
        p = c.beginPath()
        p.moveTo(12, 2.5)
        p.lineTo(20, 5.5)
        p.lineTo(20, 11.5)
        p.curveTo(20, 16.5, 16.5, 20, 12, 21.5)
        p.curveTo(7.5, 20, 4, 16.5, 4, 11.5)
        p.lineTo(4, 5.5)
        p.close()
        c.drawPath(p, stroke=1, fill=0)
    elif name == "user":
        circ(12, 8, 4)
        p = c.beginPath()
        p.moveTo(4, 21)
        p.curveTo(4, 16.5, 7.5, 14, 12, 14)
        p.curveTo(16.5, 14, 20, 16.5, 20, 21)
        c.drawPath(p, stroke=1, fill=0)
    elif name == "sun":
        circ(12, 12, 4)
        for k in range(8):
            a = k * math.pi / 4
            poly([(12 + 7.2 * math.cos(a), 12 + 7.2 * math.sin(a)), (12 + 10 * math.cos(a), 12 + 10 * math.sin(a))])
    elif name == "list":
        for yy in (6, 12, 18):
            poly([(8, yy), (21, yy)])
            circ(3.8, yy, 1, fill=1)
    c.restoreState()


def icon_badge(c, name, cx, cy, r=13, bg=SKY, fg=HANNA):
    dot(c, cx, cy, r, bg)
    s = r * 1.15
    icon(c, name, cx - s / 2, cy - s / 2, s, fg, lw=2.1)


# ── marca ───────────────────────────────────────────────────────────────────────────────────────────────────
def logo_mark(c, x, y, s=30, on_dark=False):
    """Isotipo HANNA: cuadrado redondeado con latido."""
    if on_dark:
        rrect(c, x, y, s, s, s * 0.28, fill=Color(1, 1, 1, alpha=0.16), stroke=Color(1, 1, 1, alpha=0.55), lw=0.9)
    else:
        gradient_rect(c, x, y, s, s, [ELECTRIC, HANNA, DEEP], "diag", r=s * 0.28)
    icon(c, "pulse", x + s * 0.17, y + s * 0.17, s * 0.66, WHITE, lw=2.4)


# ── gráficos ───────────────────────────────────────────────────────────────────────────────────────────────
def _arc_seg(c, cx, cy, r, a0, a1, color, thick):
    """Segmento de semicírculo entre fracciones a0..a1 (0=izquierda, 1=derecha)."""
    if a1 <= a0:
        return
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(thick)
    c.setLineCap(0)
    c.arc(cx - r, cy - r, cx + r, cy + r, 180 - 180 * a0, -180 * (a1 - a0))
    c.restoreState()


def gauge(c, cx, cy, R, thick, value, vmin, vmax, segs, label=None, unit="", ticks=()):
    """Medidor semicircular. segs: [(desde, hasta, color)] en unidades del valor."""
    r = R - thick / 2
    f = lambda v: max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
    _arc_seg(c, cx, cy, r, 0, 1, SKY, thick)
    for a, b, col in segs:
        _arc_seg(c, cx, cy, r, f(a), f(b), col, thick)
    for t, lab in ticks:
        th = math.pi * (1 - f(t))
        x1, y1 = cx + (R + 1.5) * math.cos(th), cy + (R + 1.5) * math.sin(th)
        x2, y2 = cx + (R - thick - 1.5) * math.cos(th), cy + (R - thick - 1.5) * math.sin(th)
        c.saveState()
        c.setStrokeColor(WHITE)
        c.setLineWidth(1.6)
        c.line(x1, y1, x2, y2)
        c.restoreState()
        xl, yl = cx + (R + 9) * math.cos(th), cy + (R + 9) * math.sin(th)
        text(c, lab, xl, yl - 2.5, FB, 7.4, INK3, "c")
    th = math.pi * (1 - f(value))
    mx, my = cx + r * math.cos(th), cy + r * math.sin(th)
    dot(c, mx, my, thick * 0.62, WHITE)
    c.saveState()
    c.setStrokeColor(INK)
    c.setLineWidth(2.2)
    c.circle(mx, my, thick * 0.62, stroke=1, fill=0)
    c.restoreState()
    if label is not None:
        text(c, label, cx, cy + 4, SB, R * 0.36, INK, "c")
        if unit:
            text(c, unit, cx, cy - 9, FSB, 8.5, INK3, "c")
    text(c, f"{vmin:g}", cx - r, cy - 11, FB, 7.2, INK3, "c")
    text(c, f"{vmax:.0f}", cx + r, cy - 11, FB, 7.2, INK3, "c")


def band_strip(c, x, y, w, h, value, band, attn, vmin, vmax, marker=True):
    """Barra horizontal con banda de referencia (verde) y lados según atención contextual."""
    lo, hi = band
    f = lambda v: max(0.0, min(1.0, (v - vmin) / (vmax - vmin)))
    below = AMBER if attn == "low" else CYAN
    above = AMBER if attn == "high" else CYAN
    rrect(c, x, y, w, h, h / 2, fill=SKY)
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, h / 2)
    c.clipPath(p, stroke=0, fill=0)
    for a, b, col in [(vmin, lo, below), (lo, hi, GREEN), (hi, vmax, above)]:
        c.setFillColor(col)
        c.rect(x + w * f(a), y, w * (f(b) - f(a)), h, stroke=0, fill=1)
    c.restoreState()
    if marker:
        mx = x + w * f(value)
        dot(c, mx, y + h / 2, h * 0.95, WHITE)
        c.saveState()
        c.setStrokeColor(INK)
        c.setLineWidth(1.6)
        c.circle(mx, y + h / 2, h * 0.95, stroke=1, fill=0)
        c.restoreState()


def hbar(c, x, y, w, h, frac, color=HANNA, track=SKY):
    rrect(c, x, y, w, h, h / 2, fill=track)
    if frac > 0:
        rrect(c, x, y, max(h, w * min(1, frac)), h, h / 2, fill=color)


def donut(c, cx, cy, R, thick, parts, center=None, sub=None):
    """Dona. parts: [(valor, color)]"""
    tot = sum(v for v, _ in parts) or 1
    r = R - thick / 2
    ang = 90.0
    c.saveState()
    c.setLineWidth(thick)
    c.setLineCap(0)
    for v, col in parts:
        ext = -360.0 * v / tot
        c.setStrokeColor(col)
        c.arc(cx - r, cy - r, cx + r, cy + r, ang, ext)
        ang += ext
    c.restoreState()
    if center:
        text(c, center, cx, cy - 1, SB, R * 0.42, INK, "c")
    if sub:
        text(c, sub, cx, cy - 11, FSB, 7.2, INK3, "c")


def _nice(v0, v1, n=4):
    if v1 - v0 < 1e-9:
        v0, v1 = v0 - 1, v1 + 1
    step = (v1 - v0) / n
    mag = 10 ** math.floor(math.log10(step))
    step = min((m * mag for m in (1, 1.5, 2, 2.5, 3, 4, 5, 10) if m * mag >= step), default=step)
    lo = math.floor(v0 / step) * step
    hi = math.ceil(v1 / step) * step
    return lo, hi, step


def line_chart(c, x, y, w, h, pts, fmt_x, dec=1, color=HANNA, band=None):
    """Serie temporal. pts: [(datetime, valor)]. Área (x,y,w,h) incluye ejes."""
    ml, mb, mt, mr = 30, 16, 6, 8
    px, py, pw, ph = x + ml, y + mb, w - ml - mr, h - mb - mt
    vals = [v for _, v in pts]
    v0, v1 = min(vals), max(vals)
    if band:
        v0, v1 = min(v0, band[0]), max(v1, band[1])
    pad = (v1 - v0) * 0.12 or 1
    lo, hi, step = _nice(v0 - pad, v1 + pad, 3)
    ys = lambda v: py + ph * (v - lo) / (hi - lo)
    t0, t1 = pts[0][0].timestamp(), pts[-1][0].timestamp()
    xs = (lambda t: px + pw * (t.timestamp() - t0) / (t1 - t0)) if t1 > t0 else (lambda t: px + pw / 2)
    if band:
        c.saveState()
        c.setFillColor(GREEN_T)
        c.rect(px, ys(max(lo, band[0])), pw, ys(min(hi, band[1])) - ys(max(lo, band[0])), stroke=0, fill=1)
        c.restoreState()
    v = lo
    while v <= hi + 1e-9:
        c.saveState()
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(px, ys(v), px + pw, ys(v))
        c.restoreState()
        text(c, f"{v:.{dec if step < 1 else 0}f}".replace(".", ","), px - 4, ys(v) - 2.4, F, 6.8, INK3, "r")
        v += step
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.9)
    c.setLineJoin(1)
    p = c.beginPath()
    for i, (t, val) in enumerate(pts):
        (p.moveTo if i == 0 else p.lineTo)(xs(t), ys(val))
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()
    for t, val in pts:
        dot(c, xs(t), ys(val), 3, color)
        dot(c, xs(t), ys(val), 1.3, WHITE)
    labs = [pts[0][0], pts[-1][0]] if len(pts) > 2 else [p_[0] for p_ in pts]
    for i, t in enumerate(labs):
        text(c, fmt_x(t), xs(t), y + 3, F, 6.8, INK3, "l" if i == 0 else "r")
    la, lv = pts[-1]
    lab = f"{lv:.{dec}f}".replace(".", ",")
    lx, ly = min(xs(la), px + pw), ys(lv) + 6
    rrect(c, lx - tw(lab, FB, 7.4) - 2, ly - 2, tw(lab, FB, 7.4) + 4, 10, 3, fill=WHITE)
    text(c, lab, lx, ly, FB, 7.4, color, "r" if len(pts) > 1 else "c")


def poincare(c, x, y, s, rr, sd1=None, sd2=None):
    """Diagrama de Poincaré con elipse SD1/SD2. (x,y,s) = cuadrado incluyendo ejes."""
    ml, mb = 26, 16
    px, py, ps = x + ml, y + mb, min(s - ml - 6, s - mb - 6)
    a, b = rr[:-1], rr[1:]
    v0, v1 = min(rr), max(rr)
    pad = (v1 - v0) * 0.1 or 20
    lo, hi, step = _nice(v0 - pad, v1 + pad, 3)
    m = lambda v: ps * (v - lo) / (hi - lo)
    rrect(c, px, py, ps, ps, 4, fill=ICE, stroke=LINE, lw=0.5)
    v = lo
    while v <= hi + 1e-9:
        c.saveState()
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(px + m(v), py, px + m(v), py + ps)
        c.line(px, py + m(v), px + ps, py + m(v))
        c.restoreState()
        text(c, f"{v:.0f}", px + m(v), y + 4, F, 6.6, INK3, "c")
        text(c, f"{v:.0f}", px - 3, py + m(v) - 2.3, F, 6.6, INK3, "r")
        v += step
    c.saveState()
    c.setStrokeColor(MID)
    c.setDash(2, 2)
    c.setLineWidth(0.7)
    c.line(px, py, px + ps, py + ps)
    c.restoreState()
    step_i = max(1, len(a) // 700)
    c.saveState()
    c.setFillColor(Color(0.04, 0.36, 1, alpha=0.5))
    for i in range(0, len(a), step_i):
        c.circle(px + m(a[i]), py + m(b[i]), 1.5, stroke=0, fill=1)
    c.restoreState()
    if sd1 and sd2:
        mean = sum(rr) / len(rr)
        c.saveState()
        c.translate(px + m(mean), py + m(mean))
        c.rotate(45)
        k = ps / (hi - lo)
        c.setStrokeColor(DEEP)
        c.setLineWidth(1.4)
        c.ellipse(-sd2 * k, -sd1 * k, sd2 * k, sd1 * k, stroke=1, fill=0)
        c.restoreState()


def histogram(c, x, y, w, h, rr, bins=12):
    ml, mb, mt = 8, 16, 6
    px, py, pw, ph = x + ml, y + mb, w - ml - 6, h - mb - mt
    v0, v1 = min(rr), max(rr)
    span = (v1 - v0) or 1
    cnt = [0] * bins
    for v in rr:
        cnt[min(bins - 1, int((v - v0) / span * bins))] += 1
    mx = max(cnt)
    bw = pw / bins
    for i, n in enumerate(cnt):
        bh = ph * n / mx
        rrect(c, px + i * bw + 1, py, bw - 2, bh, 1.6, fill=HANNA if n == mx else MID)
    c.saveState()
    c.setStrokeColor(LINE)
    c.line(px, py, px + pw, py)
    c.restoreState()
    text(c, f"{v0:.0f}", px, y + 3, F, 6.8, INK3, "l")
    text(c, f"{(v0 + v1) / 2:.0f} ms", px + pw / 2, y + 3, F, 6.8, INK3, "c")
    text(c, f"{v1:.0f}", px + pw, y + 3, F, 6.8, INK3, "r")


# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
# Gráficos del informe HANNA v2
# ═════════════════════════════════════════════════════════════════════════════════════════════════════════════
def fnum(v, d=1):
    return f"{v:.{d}f}".replace(".", ",")


def position_bar(c, x, y, w, value, band, attn, vmin, vmax, h=7):
    """Barra con el rango de referencia sombreado (verde), el marcador del valor y los límites rotulados."""
    band_strip(c, x, y, w, h, value, band, attn, vmin, vmax)
    f = lambda v: x + w * (v - vmin) / (vmax - vmin)
    for v in band:
        lab = f"{v:g}"
        text(c, lab, max(x + 6, min(x + w - 6, f(v))), y - 9, F, 6.6, INK3, "c")


def _axis_frac(v, lo, hi):
    """Posición 0..1 en un eje de 3 columnas iguales (bajo | en rango | alto); dentro de cada una es proporcional."""
    W = hi - lo
    amin = min(lo - 0.6 * W, v - 0.05 * W)
    amax = max(hi + 0.6 * W, v + 0.05 * W)
    cl = lambda f: min(max(f, 0.09), 0.91)
    if v < lo:
        return cl((v - amin) / (lo - amin)) / 3
    if v > hi:
        return 1 / 3 + 1 / 3 + cl((v - hi) / (amax - hi)) / 3
    return 1 / 3 + cl((v - lo) / (hi - lo)) / 3


def matrix_chart(c, x, y, w, h, mx, mini=False):
    """Mapa 3x3: columnas = RMSSD (bajo | en rango | alto), filas = FC (alta arriba | en rango | baja abajo)."""
    cw, ch = w / 3, h / 3
    rm, hr = mx["rmssd"], mx["hr"]
    xi = {"low": 0, "in": 1, "high": 2}[mx["x"]]
    yi = {"high": 0, "in": 1, "low": 2}[mx["y"]]          # fila desde arriba
    for r in range(3):
        for k in range(3):
            cx, cy = x + k * cw, y + (2 - r) * ch
            fill = GREEN_T if (k == 1 and r == 1) else (WHITE if (k + r) % 2 else ICE)
            rrect(c, cx + 1.2, cy + 1.2, cw - 2.4, ch - 2.4, 7 if not mini else 4, fill=fill, stroke=LINE, lw=0.6)
    if not (xi == 1 and yi == 1):
        pass
    cx, cy = x + xi * cw, y + (2 - yi) * ch
    rrect(c, cx + 1.2, cy + 1.2, cw - 2.4, ch - 2.4, 7 if not mini else 4, fill=SKY, stroke=HANNA, lw=2.2 if not mini else 1.6)
    if not mini:
        text(c, "rango del protocolo", x + cw * 1.5, y + ch * 1.5 + ch * 0.36, F, 6.6, GREEN_D, "c")
    # ejes y rótulos
    sx = 7.4 if not mini else 6.2
    heads = [(f"RMSSD bajo", f"< {rm['lo']:g} ms"), ("RMSSD en rango", f"{rm['lo']:g}–{rm['hi']:g} ms"), ("RMSSD alto", f"> {rm['hi']:g} ms")]
    for k, (a, b) in enumerate(heads):
        text(c, a, x + k * cw + cw / 2, y - (11 if not mini else 8), FSB, sx, INK2, "c")
        if not mini:
            text(c, b, x + k * cw + cw / 2, y - 21, F, 7, INK3, "c")
    rows = [("FC alta", f"> {hr['hi']:g} lpm"), ("FC en rango", f"{hr['lo']:g}–{hr['hi']:g} lpm"), ("FC baja", f"< {hr['lo']:g} lpm")]
    for r, (a, b) in enumerate(rows):
        yy = y + (2 - r) * ch + ch / 2
        text(c, a, x - 6, yy + (2 if not mini else 1), FSB, sx, INK2, "r")
        if not mini:
            text(c, b, x - 6, yy - 8, F, 7, INK3, "r")
    # posición exacta
    px = x + w * _axis_frac(rm["v"], rm["lo"], rm["hi"])
    fy = _axis_frac(hr["v"], hr["lo"], hr["hi"])           # 0 = abajo
    py = y + h * fy
    ex = {"low": x + cw, "in": None, "high": x + 2 * cw}[mx["x"]]
    if ex is None:
        ex = x + cw if (rm["v"] - rm["lo"]) <= (rm["hi"] - rm["v"]) else x + 2 * cw
    ey = {"low": y + ch, "high": y + 2 * ch, "in": None}[mx["y"]]
    if ey is None:
        ey = y + ch if (hr["v"] - hr["lo"]) <= (hr["hi"] - hr["v"]) else y + 2 * ch
    if not mini:
        c.saveState()
        c.setStrokeColor(DEEP)
        c.setLineWidth(1.1)
        c.setDash(3, 2.5)
        c.line(px, py, ex, py)
        c.line(px, py, px, ey)
        c.restoreState()
        for (a, b, c2, d) in [(ex, py - 3.5, ex, py + 3.5), (px - 3.5, ey, px + 3.5, ey)]:
            c.saveState(); c.setStrokeColor(DEEP); c.setLineWidth(1.4); c.line(a, b, c2, d); c.restoreState()
        dx = abs(rm["v"] - (rm["lo"] if ex <= x + cw + 0.1 else rm["hi"]))
        dy = abs(hr["v"] - (hr["lo"] if ey <= y + ch + 0.1 else hr["hi"]))
    # punto
    for rad, col in [(11 if not mini else 6.5, Color(0.04, 0.17, 0.42, alpha=0.18)), (8.5 if not mini else 5, WHITE), (6 if not mini else 3.6, HANNA)]:
        dot(c, px, py - (0 if rad > 6.5 else 0), rad, col)
    if not mini:
        def rel(v, lo, hi, d, u):
            if v < lo: return f"{fnum(lo - v, d)} {u} bajo el límite"
            if v > hi: return f"{fnum(v - hi, d)} {u} sobre el límite"
            return f"a {fnum(min(v - lo, hi - v), d)} {u} del límite"
        lab1 = f"RMSSD {fnum(rm['v'], 1)} ms · {rel(rm['v'], rm['lo'], rm['hi'], 1, 'ms')}"
        lab2 = f"FC {fnum(hr['v'], 0)} lpm · {rel(hr['v'], hr['lo'], hr['hi'], 0, 'lpm')}"
        bw_ = max(tw(lab1, FB, 7.8), tw(lab2, FB, 7.8)) + 16
        bx = min(max(px - bw_ / 2, x + 4), x + w - bw_ - 4)
        by = py + 16 if fy < 0.62 else py - 16 - 30
        by = min(max(by, y + 4), y + h - 34)
        rrect(c, bx, by, bw_, 30, 7, fill=DEEP)
        text(c, lab1, bx + 8, by + 18, FB, 7.8, WHITE)
        text(c, lab2, bx + 8, by + 7, FB, 7.8, CELESTE)


ZONE_COL = {"low": CYAN, "in": GREEN, "high": AMBER}


def tacogram(c, x, y, w, h, bt):
    """Intervalos entre latidos (NN) en el tiempo, coloreados según la FC instantánea (60-85 lpm = rango del protocolo)."""
    nn, t = bt["nn"], bt["t"]
    ml, mr, mb, mt = 38, 38, 18, 6
    px, py, pw, ph = x + ml, y + mb, w - ml - mr, h - mb - mt
    vmin, vmax = min(min(nn), 706) - 40, max(max(nn), 1000) + 40
    lo, hi, step = _nice(vmin, vmax, 4)
    T = t[-1]
    ys = lambda v: py + ph * (v - lo) / (hi - lo)
    xs = lambda s: px + pw * s / T
    c.saveState()
    c.setFillColor(GREEN_T)
    c.rect(px, ys(706.0), pw, ys(1000.0) - ys(706.0), stroke=0, fill=1)
    c.restoreState()
    v = lo
    while v <= hi + 1e-6:
        c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(px, ys(v), px + pw, ys(v)); c.restoreState()
        text(c, f"{v:.0f}", px - 4, ys(v) - 2.4, F, 6.8, INK3, "r")
        v += step
    for fc in (45, 50, 60, 70, 85, 100, 120):
        rr = 60000.0 / fc
        if lo < rr < hi:
            text(c, f"{fc}", px + pw + 5, ys(rr) - 2.4, F, 6.8, INK3, "l")
    text(c, "ms", px - 4, py + ph + 7, FB, 6.8, INK3, "r")
    text(c, "lpm", px + pw + 5, py + ph + 7, FB, 6.8, INK3, "l")
    c.saveState(); c.setStrokeColor(MID); c.setLineWidth(0.8); c.setLineJoin(1)
    p = c.beginPath()
    for i, (tt, v_) in enumerate(zip(t, nn)):
        (p.moveTo if i == 0 else p.lineTo)(xs(tt), ys(v_))
    c.drawPath(p, stroke=1, fill=0); c.restoreState()
    for tt, v_ in zip(t, nn):
        hrv = 60000.0 / v_
        col = CYAN if hrv < 60 else (AMBER if hrv > 85 else GREEN)
        dot(c, xs(tt), ys(v_), 2.1, col)
    k = 0
    while k <= T:
        text(c, f"{k:.0f} s", xs(k), y + 4, F, 6.8, INK3, "c")
        k += 30 if T > 100 else 10


def ppg_trace(c, x, y, w, h, view):
    sr, smp, pk = view["sr"], view["samples"], view["peaks"]
    ml, mb, mt = 6, 16, 14
    px, py, pw, ph = x + ml, y + mb, w - ml - 6, h - mb - mt
    lo, hi = min(smp), max(smp)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = lo - pad, hi + pad
    T = len(smp) / sr
    xs = lambda i: px + pw * i / (len(smp) - 1)
    ys = lambda v: py + ph * (v - lo) / (hi - lo)
    for k in range(0, int(T) + 1, 2):
        xx = px + pw * k / T
        c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(xx, py, xx, py + ph); c.restoreState()
        text(c, f"{k} s", xx, y + 4, F, 6.8, INK3, "c")
    c.saveState(); c.setStrokeColor(HANNA); c.setLineWidth(1.4); c.setLineJoin(1)
    p = c.beginPath()
    for i, v in enumerate(smp):
        (p.moveTo if i == 0 else p.lineTo)(xs(i), ys(v))
    c.drawPath(p, stroke=1, fill=0); c.restoreState()
    for j, i in enumerate(pk):
        dot(c, xs(i), ys(smp[i]), 3.2, WHITE)
        c.saveState(); c.setStrokeColor(DEEP); c.setLineWidth(1.4); c.circle(xs(i), ys(smp[i]), 3.2, stroke=1, fill=0); c.restoreState()
        if j:
            ms = (pk[j] - pk[j - 1]) / sr * 1000.0
            text(c, f"{ms:.0f}", (xs(pk[j]) + xs(pk[j - 1])) / 2, py + ph + 3, FB, 6.6, DEEP, "c")


def beat_train(c, x, y, w, h, bt):
    """Tren de latidos reales (cada marca es un latido; la altura no es amplitud)."""
    i0, i1 = bt["win"]
    t, nn = bt["t"], bt["nn"]
    base_t = t[i0] - nn[i0] / 1000.0
    T = max(1.0, t[i1 - 1] - base_t)
    ml, mb, mt = 6, 16, 16
    px, pw = x + ml, w - ml - 6
    ybase = y + mb + 6
    top = y + h - mt
    xs = lambda s: px + pw * (s - base_t) / T
    c.saveState(); c.setStrokeColor(MID); c.setLineWidth(1); c.line(px, ybase, px + pw, ybase); c.restoreState()
    for k in range(0, int(T) + 1, 2):
        text(c, f"{k} s", px + pw * k / T, y + 3, F, 6.8, INK3, "c")
    prev = None
    for i in range(i0, i1):
        xx = xs(t[i])
        c.saveState(); c.setStrokeColor(HANNA); c.setLineWidth(2); c.setLineCap(1); c.line(xx, ybase, xx, top - 10); c.restoreState()
        dot(c, xx, top - 10, 3.4, HANNA)
        if prev is not None:
            mid = (xx + prev) / 2
            c.saveState(); c.setStrokeColor(MID); c.setLineWidth(0.7); c.line(prev, top - 2, xx, top - 2)
            c.line(prev, top - 4.5, prev, top + 0.5); c.line(xx, top - 4.5, xx, top + 0.5); c.restoreState()
            text(c, f"{nn[i]:.0f}", mid, top + 2.5, FB, 6.6, DEEP, "c")
        prev = xx


def quality_bar(c, x, y, w, h, valid_pct):
    rrect(c, x, y, w, h, h / 2, fill=CELESTE)
    rrect(c, x, y, max(h, w * valid_pct / 100.0), h, h / 2, fill=HANNA)


LEVEL_COL = {"bajo": CELESTE, "moderado": MID, "alto": ELECTRIC, "muy alto": DEEP}


def loads_map(c, x, y, s, phys, emo, auto, stress):
    """Mapa X = carga física, Y = carga emocional (0-100). Tamaño = carga autonómica; anillo = nivel de estrés (si existe)."""
    ml, mb = 30, 24
    px, py, ps = x + ml, y + mb, s - ml - 8
    f = lambda v: ps * v / 100.0
    rrect(c, px, py, ps, ps, 6, fill=ICE, stroke=LINE, lw=0.6)
    for a, b, col in [(0, 25, None), (25, 55, None), (55, 100, None)]:
        pass
    c.saveState(); c.setFillColor(Color(0.04, 0.36, 1, alpha=0.05)); c.rect(px + f(55), py, ps - f(55), ps, stroke=0, fill=1); c.rect(px, py + f(55), ps, ps - f(55), stroke=0, fill=1); c.restoreState()
    for v in (25, 55):
        c.saveState(); c.setStrokeColor(MID); c.setLineWidth(0.8); c.setDash(3, 3)
        c.line(px + f(v), py, px + f(v), py + ps); c.line(px, py + f(v), px + ps, py + f(v)); c.restoreState()
    for v in (0, 25, 55, 100):
        text(c, f"{v}", px + f(v), y + 14, F, 6.8, INK3, "c")
        text(c, f"{v}", px - 4, py + f(v) - 2.3, F, 6.8, INK3, "r")
    text(c, "Carga física", px + ps / 2, y + 3, FSB, 7.6, INK2, "c")
    c.saveState(); c.translate(x + 7, py + ps / 2); c.rotate(90); text(c, "Carga emocional", 0, 0, FSB, 7.6, INK2, "c"); c.restoreState()
    cx, cy = px + f(phys), py + f(emo)
    r = 9 + 17 * auto / 100.0
    ring = LEVEL_COL.get(stress["level"]) if stress and stress.get("level") else None
    dot(c, cx, cy, r + (5 if ring else 0), ring if ring else WHITE)
    dot(c, cx, cy, r, HANNA)
    dot(c, cx, cy, 2.4, WHITE)
    return {"cx": cx, "cy": cy, "r": r}


def hbar_levels(c, x, y, w, value):
    """Barra 0-100 con cortes de nivel 25 / 55 / 78."""
    rrect(c, x, y, w, 7, 3.5, fill=SKY)
    rrect(c, x, y, max(7, w * value / 100.0), 7, 3.5, fill=HANNA)
    for v in (25, 55, 78):
        c.saveState(); c.setStrokeColor(WHITE); c.setLineWidth(1.4); c.line(x + w * v / 100, y - 1, x + w * v / 100, y + 8); c.restoreState()


MARK = {"polar_h10": "o", "rr_upload": "o", "camera_ppg": "s", "face_rppg": "t", "vibration_scg": "t"}


def marker(c, kind, x, y, r, fill, stroke=None):
    c.saveState()
    c.setFillColor(fill)
    if stroke is not None:
        c.setStrokeColor(stroke); c.setLineWidth(1.4)
    if kind == "s":
        c.rect(x - r, y - r, 2 * r, 2 * r, stroke=1 if stroke is not None else 0, fill=1)
    elif kind == "t":
        p = c.beginPath(); p.moveTo(x, y + r * 1.15); p.lineTo(x - r * 1.1, y - r * 0.8); p.lineTo(x + r * 1.1, y - r * 0.8); p.close()
        c.drawPath(p, stroke=1 if stroke is not None else 0, fill=1)
    else:
        c.circle(x, y, r, stroke=1 if stroke is not None else 0, fill=1)
    c.restoreState()


def evo_chart(c, x, y, w, h, pts, fmt_x, dec=1, color=HANNA, band=None):
    """Evolución con escala propia. pts: [(datetime, valor, sensor)]. Con menos de 3 puntos no se unen con línea."""
    ml, mb, mt, mr = 34, 16, 8, 10
    px, py, pw, ph = x + ml, y + mb, w - ml - mr, h - mb - mt
    vals = [p[1] for p in pts]
    v0, v1 = min(vals), max(vals)
    if band:
        v0, v1 = min(v0, band[0]), max(v1, band[1])
    pad = (v1 - v0) * 0.18 or max(1.0, abs(v1) * 0.1)
    lo, hi, step = _nice(v0 - pad, v1 + pad, 3)
    ys = lambda v: py + ph * (v - lo) / (hi - lo)
    t0, t1 = pts[0][0].timestamp(), pts[-1][0].timestamp()
    xs = (lambda t: px + 14 + (pw - 28) * (t.timestamp() - t0) / (t1 - t0)) if t1 > t0 else (lambda t: px + pw / 2)
    if band:
        c.saveState(); c.setFillColor(GREEN_T)
        c.rect(px, ys(max(lo, band[0])), pw, ys(min(hi, band[1])) - ys(max(lo, band[0])), stroke=0, fill=1); c.restoreState()
    v = lo
    while v <= hi + 1e-9:
        c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(px, ys(v), px + pw, ys(v)); c.restoreState()
        text(c, f"{v:.{dec if step < 1 else 0}f}".replace(".", ","), px - 4, ys(v) - 2.4, F, 6.8, INK3, "r")
        v += step
    if len(pts) >= 3:
        c.saveState(); c.setStrokeColor(color); c.setLineWidth(1.4); c.setLineJoin(1)
        p = c.beginPath()
        for i, (t, val, _) in enumerate(pts):
            (p.moveTo if i == 0 else p.lineTo)(xs(t), ys(val))
        c.drawPath(p, stroke=1, fill=0); c.restoreState()
    for t, val, sensor in pts:
        marker(c, MARK.get(sensor, "o"), xs(t), ys(val), 4.4, WHITE, color)
        marker(c, MARK.get(sensor, "o"), xs(t), ys(val), 2.2, color)
    for i, (t, val, _) in enumerate(pts):
        if i in (0, len(pts) - 1) or len(pts) <= 4:
            lab = f"{val:.{dec}f}".replace(".", ",")
            text(c, lab, xs(t), ys(val) + 8, FB, 7.2, DEEP, "c")
    for i, (t, _, _) in enumerate(pts):
        if i in (0, len(pts) - 1) or len(pts) <= 4:
            text(c, fmt_x(t), xs(t), y + 3, F, 6.8, INK3, "c")

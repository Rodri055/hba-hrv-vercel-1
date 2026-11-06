"""
HBA-HRV · report/pdf.py
Maquetación del informe A4. Recibe el modelo de engine.build_model() y devuelve los bytes del PDF.
Cada página se dibuja en un marco fijo; los textos se ajustan a su caja (ver draw.para) para que nada se corte.
"""
import math
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from . import draw as D
from .draw import (AMBER, AMBER_T, CELESTE, CYAN, DEEP, ELECTRIC, F, FB, FSB, GREEN, HANNA, ICE, INK, INK2, INK3,
                   LINE, MID, RED, SB, SKY, SSB, TONE, WHITE)

PW, PH = A4
M = 40
CW = PW - 2 * M
FOOT_Y = 36
Y = lambda top: PH - top  # coordenada desde el borde superior


# ── componentes comunes ─────────────────────────────────────────────────────────────────────────────────────
def frame(c, mdl, title, sub, n, total):
    D.logo_mark(c, M, Y(52), 24)
    D.text(c, "HBA-HRV", M + 31, Y(41), SB, 11, DEEP)
    D.text(c, "Informe de evaluación HRV", PW - M, Y(36), FSB, 8, INK3, "r")
    D.text(c, f"Paciente {mdl['patient']['id']}  ·  {mdl['report_id']}", PW - M, Y(47), F, 7.4, INK3, "r", max_w=300)
    c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.7); c.line(M, Y(62), PW - M, Y(62)); c.restoreState()
    D.text(c, title, M, Y(90), SB, 18, DEEP, max_w=CW)
    D.rrect(c, M, Y(98), 30, 3, 1.5, fill=HANNA)
    if sub:
        D.para(c, sub, M, Y(106), CW, F, 8.6, INK3, max_h=24)
    footer(c, mdl, n, total)


def footer(c, mdl, n, total):
    c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(M, FOOT_Y + 12, PW - M, FOOT_Y + 12); c.restoreState()
    D.text(c, f"Informe confidencial · generado el {mdl['generated']} · no constituye diagnóstico médico", M, FOOT_Y, F, 6.8, INK3, max_w=CW - 80)
    D.text(c, f"Página {n} de {total}", PW - M, FOOT_Y, FSB, 7.2, INK2, "r")


def section(c, title, x, top, w, icon=None):
    off = 0
    if icon:
        D.icon_badge(c, icon, x + 9, Y(top) - 9, 9, SKY, HANNA)
        off = 24
    D.text(c, title, x + off, Y(top) - 12.5, SSB, 11.2, DEEP, max_w=w - off)
    return 24


def evidence_chip(c, x, y, ev, align="l"):
    if not ev:
        return 0
    lab = {"solid": "Hallazgo sólido", "possible": "Tendencia posible", "insufficient": "Datos insuficientes"}[ev["level"]]
    size = 7
    w = D.tw(lab, FB, size) + 12
    x0 = x if align == "l" else x - w
    if ev["level"] == "solid":
        D.rrect(c, x0, y - 3.4, w, size + 6.2, (size + 6.2) / 2, fill=DEEP); D.text(c, lab, x0 + 6, y, FB, size, WHITE)
    elif ev["level"] == "possible":
        D.rrect(c, x0, y - 3.4, w, size + 6.2, (size + 6.2) / 2, fill=SKY); D.text(c, lab, x0 + 6, y, FB, size, DEEP)
    else:
        D.rrect(c, x0, y - 3.4, w, size + 6.2, (size + 6.2) / 2, fill=WHITE, stroke=MID, lw=0.8, dash=([2, 2], 0)); D.text(c, lab, x0 + 6, y, FB, size, INK3)
    return w


def status_label(r):
    if r["state"] == "invalid":
        return "No interpretable"
    return "Sin referencia" if r["state"] == "none" else {"in": "Dentro de la banda", "low": "Por debajo de la banda", "high": "Por encima de la banda"}[r["state"]]


def placeholder(c, x, top, w, h, title, msg):
    D.rrect(c, x, Y(top) - h, w, h, 12, fill=ICE, stroke=MID, lw=0.8, dash=([3, 3], 0))
    D.icon(c, "info", x + w / 2 - 9, Y(top) - h / 2 + 4, 18, MID)
    D.text(c, title, x + w / 2, Y(top) - h / 2 - 12, FSB, 8.6, INK2, "c", max_w=w - 20)
    D.para(c, msg, x + 16, Y(top) - h / 2 - 20, w - 32, F, 7.6, INK3, max_h=h / 2 - 22, align=1)


def tone_of(kind):
    return {"ok": "green", "attn": "amber", "alert": "red", "info": "cyan"}.get(kind, "blue")


# ── PÁGINA 1: portada + resumen ejecutivo ────────────────────────────────────────────────────────────────────
def page_cover(c, mdl, n, total):
    D.gradient_rect(c, 0, Y(250), PW, 250, [DEEP, HANNA, ELECTRIC], "diag")
    c.saveState()
    c.setFillColor(D.Color(1, 1, 1, alpha=0.07)); c.circle(PW - 60, Y(40), 120, stroke=0, fill=1); c.circle(PW - 190, Y(235), 70, stroke=0, fill=1)
    c.setStrokeColor(D.Color(0.66, 0.83, 1, alpha=0.5)); c.setLineWidth(2); c.setLineJoin(1)
    p = c.beginPath(); pts = [(0, 172), (150, 172), (170, 150), (192, 196), (212, 160), (228, 172), (360, 172), (382, 140), (408, 200), (430, 160), (446, 172), (PW, 172)]
    p.moveTo(pts[0][0], Y(pts[0][1]))
    for px, py in pts[1:]: p.lineTo(px, Y(py))
    c.drawPath(p, stroke=1, fill=0); c.restoreState()
    D.logo_mark(c, M, Y(66), 32, on_dark=True)
    D.text(c, "HBA-HRV", M + 42, Y(50), SB, 16, WHITE)
    D.text(c, "Biometría y variabilidad del ritmo cardíaco", M + 42, Y(63), F, 8.4, CELESTE)
    w = D.tw(mdl["report_id"], FB, 8) + 16
    D.rrect(c, PW - M - w, Y(58), w, 18, 9, stroke=D.Color(1, 1, 1, alpha=0.7), lw=0.9)
    D.text(c, mdl["report_id"], PW - M - w / 2, Y(51.5), FB, 8, WHITE, "c")
    D.text(c, "INFORME DE", M, Y(122), SB, 29, WHITE)
    D.text(c, "EVALUACIÓN HRV", M, Y(154), SB, 29, WHITE)
    D.text(c, f"Medición del {mdl['when']}", M, Y(190), FSB, 10.5, CELESTE)

    p, q = mdl["patient"], mdl["quality"]
    top, h = 214, 124
    D.card(c, M, Y(top) - h, CW, h, 14)
    cw = CW / 3
    sex = {"M": "Masculino", "F": "Femenino"}.get(p["sex"], "No registrado")
    durs = f"{mdl['duration']:g} min" if mdl["duration"] else "No registrada"
    fields = [
        [("Paciente", p["id"]), ("Edad", f"{p['age']:g} años" if p["age"] is not None else "No registrada"), ("Sexo", sex)],
        [("Fecha y hora de medición", mdl["when"]), ("Método de medición", mdl["method"]), ("Duración del registro", durs)],
    ]
    for r_i, row in enumerate(fields):
        for c_i, (lab, val) in enumerate(row):
            x = M + 16 + c_i * cw
            D.text(c, lab, x, Y(top) - (20 + r_i * 38), FB, 7.2, INK3)
            D.text(c, val, x, Y(top) - (34 + r_i * 38), FSB, 10.2, INK, max_w=cw - 22)
    yb = Y(top) - 98
    D.text(c, "Calidad de la señal", M + 16, yb, FB, 7.2, INK3)
    tone = {"ok": "green", "warn": "amber", "bad": "red", "na": "blue"}[q["level"]]
    D.chip(c, M + 16, yb - 14, q["label"], tone, 8, solid=True)
    D.para(c, q["detail"], M + 16 + D.tw(q["label"], FB, 8) + 22, yb - 7.5, cw - 70, F, 7.4, INK3, max_h=22)
    D.text(c, "Contexto registrado", M + 16 + cw, yb, FB, 7.2, INK3)
    ctx = p["comorbidities"] or "Sin comorbilidades registradas"
    D.para(c, ctx, M + 16 + cw, yb - 5, 2 * cw - 30, FSB, 8.8, INK, max_h=24)

    # KPIs
    kp = [r for k in D_cover_keys() for r in mdl["indicators"] if r["key"] == k][:4]
    top2 = 356
    n_k = max(1, len(kp)); gap = 10; kw = (CW - (n_k - 1) * gap) / n_k
    for i, r in enumerate(kp):
        x = M + i * (kw + gap)
        D.card(c, x, Y(top2) - 84, kw, 84, 12)
        col = TONE[r["color"]][0]
        D.gradient_rect(c, x, Y(top2) - 4, kw, 4, [col, col], "h")
        D.text(c, r["short"], x + 12, Y(top2) - 22, FB, 8, INK3, max_w=kw - 20)
        D.text(c, r["text"], x + 12, Y(top2) - 49, SB, 22, INK, max_w=kw - 20)
        if r["unit"]:
            D.text(c, r["unit"], x + 12 + D.tw(r["text"], SB, 22) + 3, Y(top2) - 49, FSB, 8.4, INK3)
        D.chip(c, x + 12, Y(top2) - 71, status_label(r), r["color"], 6.8)

    # resumen general
    t3 = 462
    section(c, "RESUMEN GENERAL", M, t3, CW, "list")
    hh = D.para(c, mdl["summary"], M, Y(t3 + 28), CW, F, 9.2, INK, leading=12.6, max_h=96)
    t4 = t3 + 28 + hh + 12
    D.text(c, "Puntos relevantes", M, Y(t4) - 8, FSB, 9.2, INK2)
    avail = Y(t4 + 16) - 214
    fnd = mdl["findings"]
    keep = D.fit_items([t for _, t in fnd], CW, 8.7, 4.2, avail)
    D.bullets(c, keep, M, Y(t4 + 16), CW, 8.7, 4.2, [tone_of(k) for k, _ in fnd][:len(keep)], max_h=avail)
    panorama(c, mdl, 652)
    # nota
    D.rrect(c, M, 84, CW, 34, 10, fill=ICE, stroke=LINE)
    D.icon(c, "shield", M + 12, 93, 15, HANNA)
    D.para(c, "Este informe describe los resultados de una medición fisiológica y ofrece orientación general de seguimiento. No emite diagnósticos.", M + 36, 112, CW - 48, F, 8, INK2, max_h=28)
    footer(c, mdl, n, total)


def panorama(c, mdl, top):
    inds = [r for r in mdl["indicators"] if r["state"] not in ("none", "invalid")]
    nref = len(mdl["indicators"]) - len(inds)
    if not inds or mdl["alerts"]["severity"] == "invalid":
        return
    cnt = {k: sum(1 for r in inds if r["color"] == k) for k in ("green", "amber", "cyan")}
    D.card(c, M, Y(top) - 62, CW, 62, 12)
    D.text(c, "Panorama de indicadores", M + 14, Y(top) - 19, FSB, 9.2, INK)
    n = len(inds); bx, bw = M + 14, CW - 28; x = bx
    for k in ("green", "amber", "cyan"):
        if cnt[k]:
            w = bw * cnt[k] / n
            D.rrect(c, x + 0.8, Y(top) - 34, max(2, w - 1.6), 9, 4.5, fill=TONE[k][0]); x += w
    lab = [("green", "dentro de su banda"), ("amber", "fuera, requieren contexto"), ("cyan", "fuera, informativos")]
    x = M + 14
    for k, t in lab:
        if cnt[k]:
            D.dot(c, x + 3, Y(top) - 47.5, 3, TONE[k][0]); txt = f"{cnt[k]} {t}"
            D.text(c, txt, x + 10, Y(top) - 50, F, 7.6, INK2); x += D.tw(txt, F, 7.6) + 24
    if nref:
        D.text(c, f"{nref} sin referencia definida", PW - M - 14, Y(top) - 50, F, 7.6, INK3, "r")


def D_cover_keys():
    from .references import COVER_KPI
    return COVER_KPI


# ── PÁGINA 2: resultados biométricos ────────────────────────────────────────────────────────────────────────
ROWS_PER_PAGE, ROW_H, ROW_GAP = 8, 74, 3


def page_results(c, mdl, n, total, chunk, part, parts):
    sub = "Indicadores calculados por HBA-HRV en esta medición. Las bandas son umbrales operativos del protocolo HBA, no normas poblacionales."
    frame(c, mdl, "Resultados biométricos" + (f" ({part}/{parts})" if parts > 1 else ""), sub, n, total)
    x = M
    for lab, tone in [("Dentro de la banda", "green"), ("Fuera: atención contextual", "amber"), ("Fuera: informativo", "cyan"), ("Sin referencia", "blue")]:
        x += D.chip(c, x, Y(141), lab, tone, 6.8) + 6
    top = 152
    for r in chunk:
        y = Y(top) - ROW_H
        D.card(c, M, y, CW, ROW_H, 10)
        col = TONE[r["color"]][0]
        D.rrect(c, M, y, 5, ROW_H, 2.5, fill=col)
        lx = M + 16
        D.text(c, r["name"], lx, y + ROW_H - 17, FSB, 9.2, INK, max_w=140)
        D.text(c, r["text"], lx, y + ROW_H - 42, SB, 19, INK, max_w=110)
        if r["unit"]:
            D.text(c, r["unit"], lx + D.tw(r["text"], SB, 19) + 3, y + ROW_H - 42, FSB, 8.4, INK3)
        D.chip(c, lx, y + 9, status_label(r), r["color"], 6.8)
        mx = M + 168
        hm = D.para(c, r["measures"], mx, y + ROW_H - 8, 228, F, 7.2, INK3, leading=8.8, max_h=19)
        hq = D.para(c, r["meaning"], mx, y + ROW_H - 8 - hm - 2.5, 228, F, 7.5, INK, leading=9.2, max_h=ROW_H - 16 - hm - (9 if r["extra"] else 0))
        if r["extra"]:
            D.text(c, r["extra"], mx, y + 6, F, 6.8, INK3, max_w=228)
        rx = M + 410
        D.text(c, "Referencia", rx, y + ROW_H - 17, FB, 6.8, INK3)
        D.para(c, r["band_text"] or "Sin referencia definida", rx, y + ROW_H - 21, 96, FSB, 7.8, INK, leading=9.2, max_h=30)
        evidence_chip(c, rx, y + 9, r["evidence"])
        top += ROW_H + ROW_GAP
    if part == parts and Y(top) - 56 >= 236:
        color_criteria(c, mdl, top + 6)


def color_criteria(c, mdl, top):
    h = 224
    D.card(c, M, Y(top) - h, CW, h, 12)
    section(c, "Cómo leer los colores", M + 12, top + 8, CW - 24, "info")
    items = [("green", "Verde", "El valor está dentro de la banda de referencia del indicador."),
             ("amber", "Ámbar", "El valor está fuera de la banda hacia el lado que, según el protocolo, requiere atención contextual. No es un diagnóstico."),
             ("cyan", "Celeste", "El valor está fuera de la banda hacia el lado informativo. No se califica como bueno ni malo."),
             ("blue", "Azul", "Indicador sin banda definida en el protocolo: se muestra sin clasificar."),
             ("red", "Rojo", "Reservado para alertas técnicas de validez de la señal (valores fisiológicamente imposibles o exceso de artefactos).")]
    y = top + 38
    for tone, name, desc in items:
        D.dot(c, M + 22, Y(y) - 5, 5, TONE[tone][0])
        D.text(c, name, M + 36, Y(y) - 8, FSB, 8.4, INK)
        hh = D.para(c, desc, M + 92, Y(y) - 0.5, CW - 108, F, 8, INK2, leading=10, max_h=26)
        y += max(22, hh + 8)
    have = {r["key"] for r in mdl["indicators"]}
    from .references import ORDER, INDICATORS
    miss = [INDICATORS[k]["short"] for k in ORDER if k not in have and k not in ("mean_rr", "resp_rate_rpm")]
    D.para(c, "Las bandas dependen del indicador, de la edad y el sexo (en el RMSSD) y de las condiciones de medición. No existe un rango universal.", M + 16, Y(y + 2), CW - 32, F, 7.6, INK3, max_h=22)
    if miss:
        D.para(c, "No calculados en esta medición: " + ", ".join(miss) + ".", M + 16, Y(y + 26), CW - 32, FSB, 7.8, INK2, max_h=24)


# ── PÁGINA 3: gráficos ──────────────────────────────────────────────────────────────────────────────────────
def chart_card(c, x, top, w, h, title, icon_name):
    D.card(c, x, Y(top) - h, w, h, 12)
    D.icon_badge(c, icon_name, x + 17, Y(top) - 19, 9.5, SKY, HANNA)
    D.text(c, title, x + 32, Y(top) - 22, FSB, 9.4, INK, max_w=w - 44)


def caption(c, x, bottom, w, s, h=36):
    D.para(c, s, x, bottom + h, w, F, 7.2, INK3, leading=9, max_h=h)


def page_charts(c, mdl, n, total):
    frame(c, mdl, "Gráficos e interpretación visual", "Cada gráfico se construye solo con los datos de esta medición. Los colores siguen el criterio explicado en la página 2.", n, total)
    if mdl["alerts"]["severity"] == "invalid":
        D.card(c, M, Y(130) - 250, CW, 250, 14)
        D.icon_badge(c, "alert", M + 40, Y(130) - 44, 20, D.RED_T, D.RED)
        D.text(c, "Gráficos no disponibles por la validez de la señal", M + 74, Y(130) - 42, SSB, 12.5, DEEP, max_w=CW - 90)
        D.para(c, "Para no inducir a error, no se grafican los valores frente a sus bandas cuando la señal presenta inconsistencias técnicas. Estos son los motivos detectados:", M + 24, Y(130) - 68, CW - 48, F, 8.8, INK2, leading=11.6, max_h=40)
        tones = ["red" if i["level"] == "invalid" else "amber" for i in mdl["alerts"]["issues"]]
        D.bullets(c, [f"{i['field']}: {i['msg']}" for i in mdl["alerts"]["issues"]], M + 24, Y(130) - 116, CW - 48, 8.8, 5, tones, max_h=90)
        D.text(c, "Qué hacer", M + 24, Y(130) - 206, FSB, 9.2, INK)
        D.para(c, "Repetir la medición con el sensor bien colocado, en reposo, sin hablar ni moverse y con luz estable (si usa cámara). Siga las indicaciones de preparación de la aplicación.", M + 24, Y(130) - 214, CW - 48, F, 8.6, INK2, leading=11, max_h=30)
        return
    byk = {r["key"]: r for r in mdl["indicators"]}
    W2, G = (CW - 12) / 2, 12
    t1, h1 = 130, 206
    # 1) medidor RMSSD
    xL = M
    r = byk.get("rmssd")
    if r and r["band"]:
        lo, hi = r["band"]; vmax = max(hi * 1.7, r["value"] * 1.12)
        chart_card(c, xL, t1, W2, h1, "RMSSD frente a su referencia", "heart")
        D.gauge(c, xL + W2 / 2, Y(t1) - 130, 84, 17, r["value"], 0, vmax, [(0, lo, AMBER), (lo, hi, GREEN), (hi, vmax, CYAN)], r["text"], "ms", [(lo, f"{lo:g}"), (hi, f"{hi:g}")])
        caption(c, xL + 14, Y(t1) - h1 + 8, W2 - 28, f"Verde: referencia del protocolo para su edad y sexo ({r['band_text']}). Ámbar: por debajo; celeste: por encima. El círculo blanco marca el valor medido.", 30)
    else:
        placeholder(c, xL, t1, W2, h1, "RMSSD no disponible", "No se calculó el RMSSD en esta medición.")
    # 2) otros indicadores
    xR = M + W2 + G
    rows = [byk[k] for k in ("hr_mean", "sdnn", "lf_hf", "sd1", "sd2", "dfa_alpha1", "baevsky") if k in byk and byk[k]["band"]][:5]
    if rows:
        chart_card(c, xR, t1, W2, h1, "Otros indicadores frente a sus bandas", "chart")
        yy = t1 + 42
        for rr_ in rows:
            lo, hi = rr_["band"]; vmax = max(hi * 1.8, rr_["value"] * 1.12)
            D.text(c, rr_["short"], xR + 14, Y(yy) , FSB, 8, INK2)
            D.text(c, f"{rr_['text']} {rr_['unit']}".strip(), xR + W2 - 14, Y(yy), SB, 8.6, INK, "r")
            D.band_strip(c, xR + 14, Y(yy) - 14, W2 - 28, 6, rr_["value"], rr_["band"], D_attn(rr_["key"]), 0, vmax)
            f = lambda v: xR + 14 + (W2 - 28) * v / vmax
            D.text(c, f"{lo:g}", f(lo), Y(yy) - 24, F, 6.4, INK3, "c"); D.text(c, f"{hi:g}", f(hi), Y(yy) - 24, F, 6.4, INK3, "c")
            yy += 25
        caption(c, xR + 14, Y(t1) - h1 + 6, W2 - 28, "Verde: dentro de la banda del protocolo. Ámbar: fuera hacia el lado que requiere contexto; celeste: fuera hacia el lado informativo.", 24)
    else:
        placeholder(c, xR, t1, W2, h1, "Sin bandas disponibles", "Ningún otro indicador de esta medición tiene una banda de referencia definida.")
    # 3) HF/LF + 4) cargas
    t2, h2 = t1 + h1 + 10, 186
    m_ = mdl["metrics"]
    lf, hf = m_["lf_power"], m_["hf_power"]
    if lf is not None and hf is not None and lf + hf > 0:
        chart_card(c, xL, t2, W2, h2, "Balance de potencia HF / LF", "pulse")
        p_hf = hf / (lf + hf) * 100
        D.donut(c, xL + 70, Y(t2) - 94, 46, 14, [(hf, HANNA), (lf, CELESTE)], f"{p_hf:.0f}%", "HF")
        lx = xL + 138
        D.dot(c, lx, Y(t2) - 78, 4, HANNA); D.text(c, f"HF (vagal): {p_hf:.0f} %", lx + 10, Y(t2) - 81, FSB, 8.4, INK)
        D.dot(c, lx, Y(t2) - 98, 4, CELESTE); D.text(c, f"LF: {100 - p_hf:.0f} %", lx + 10, Y(t2) - 101, FSB, 8.4, INK)
        if m_["lf_hf"] is not None:
            D.text(c, f"LF/HF: {m_['lf_hf']:.2f}".replace(".", ","), lx, Y(t2) - 122, F, 8, INK3)
        cap = "Reparto de la potencia espectral entre HF y LF. LF no equivale estrictamente a actividad simpática."
        if (mdl["duration"] or 0) < 5:
            cap += " Con registros menores a 5 min es orientativo."
        caption(c, xL + 14, Y(t2) - h2 + 6, W2 - 28, cap, 30)
    else:
        placeholder(c, xL, t2, W2, h2, "Balance HF / LF no disponible", "No se calcularon las potencias LF y HF en esta medición (requiere registro suficiente).")
    if mdl["cargas"]:
        chart_card(c, xR, t2, W2, h2, "Cargas autonómicas (protocolo HBA)", "target")
        yy = t2 + 46
        for _, lab, v in mdl["cargas"]:
            D.text(c, lab, xR + 14, Y(yy), FSB, 8, INK2)
            D.text(c, f"{v['value']:.0f}" + (f" · {v['level']}" if v["level"] else ""), xR + W2 - 14, Y(yy), SB, 8.4, INK, "r")
            D.hbar(c, xR + 14, Y(yy) - 12, W2 - 28, 6, v["value"] / 100, HANNA)
            yy += 27
        caption(c, xR + 14, Y(t2) - h2 + 6, W2 - 28, "Escala 0–100: un valor mayor indica mayor carga. Son índices compuestos del protocolo HBA, no un criterio diagnóstico.", 24)
    else:
        placeholder(c, xR, t2, W2, h2, "Cargas no disponibles", "Esta medición no incluye los índices de carga del protocolo HBA.")
    # 5) distribución RR
    t3, h3 = t2 + h2 + 10, 178
    rr = mdl["rr"]
    if rr:
        chart_card(c, M, t3, CW, h3, "Distribución de los intervalos RR", "chart")
        D.text(c, "Histograma de intervalos (ms)", M + 16, Y(t3) - 46, FB, 7.4, INK3)
        D.histogram(c, M + 10, Y(t3) - h3 + 36, 230, h3 - 92, rr, 12)
        D.text(c, "Diagrama de Poincaré", M + 270, Y(t3) - 46, FB, 7.4, INK3)
        D.poincare(c, M + 262, Y(t3) - h3 + 36, h3 - 84, rr, m_["sd1"], m_["sd2"])
        sx = M + 262 + h3 - 70
        D.text(c, f"{len(rr)} latidos", sx, Y(t3) - 62, FSB, 8.4, INK)
        D.text(c, f"RR medio {sum(rr) / len(rr):.0f} ms", sx, Y(t3) - 75, F, 7.6, INK3)
        if m_["sd1"] is not None and m_["sd2"] is not None:
            D.text(c, f"SD1 {m_['sd1']:.1f} ms".replace(".", ","), sx, Y(t3) - 92, F, 7.6, INK3)
            D.text(c, f"SD2 {m_['sd2']:.1f} ms".replace(".", ","), sx, Y(t3) - 104, F, 7.6, INK3)
        D.para(c, "Los intervalos son los registrados antes de depurar artefactos. La elipse del Poincaré resume SD1 (corto plazo) y SD2 (largo plazo).", sx, Y(t3) - 118, M + CW - sx - 12, F, 6.9, INK3, leading=8.4, max_h=44)
        caption(c, M + 14, Y(t3) - h3 + 4, 240, "Una distribución estrecha indica menor variabilidad; una más ancha, mayor variabilidad.", 22)
    else:
        why = "Este método no entrega los intervalos RR individuales." if mdl["sensor"] in ("camera_ppg", "face_rppg", "vibration_scg") else "No se dispone de la serie de intervalos RR de esta medición."
        placeholder(c, M, t3, CW, h3, "Distribución de intervalos RR no disponible", why + " Los indicadores se calcularon igualmente a partir de la señal procesada.")


def D_attn(key):
    from .references import INDICATORS
    return INDICATORS[key]["attn"]


# ── PÁGINA 4: qué significan los resultados ────────────────────────────────────────────────────────────────
def page_meaning(c, mdl, n, total):
    frame(c, mdl, "¿Qué significan mis resultados?", "Se separa lo observado, la interpretación fisiológica posible y lo que merece seguimiento. Ningún valor aislado indica enfermedad ni buena salud.", n, total)
    cols = [(M + 14, "Resultado observado", 142), (M + 170, "Interpretación fisiológica posible", 190), (M + 376, "Aspectos a seguir", 128)]
    for x, lab, _ in cols:
        D.text(c, lab, x, Y(142), FSB, 8.2, INK2)
    top, rh = 150, 82
    for r in mdl["interp"]:
        y = Y(top) - rh
        D.card(c, M, y, CW, rh, 10)
        D.rrect(c, M, y, 5, rh, 2.5, fill=TONE[r["color"]][0])
        D.para(c, r["observed"], cols[0][0], y + rh - 8, cols[0][2], FSB, 7.8, INK, leading=9.6, max_h=rh - 30)
        evidence_chip(c, cols[0][0], y + 9, r["evidence"])
        D.para(c, r["meaning"], cols[1][0], y + rh - 8, cols[1][2], F, 7.6, INK, leading=9.4, max_h=rh - 14)
        D.para(c, r["follow"], cols[2][0], y + rh - 8, cols[2][2], F, 7.4, INK2, leading=9, max_h=rh - 14)
        top += rh + 5
    # leyenda de niveles de evidencia
    lh = 58
    D.rrect(c, M, Y(top) - lh, CW, lh, 10, fill=ICE, stroke=LINE)
    D.text(c, "Cómo se clasifica la solidez de cada lectura", M + 14, Y(top) - 17, FSB, 8.6, INK)
    leg = [({"level": "solid"}, "Método directo, señal sin alertas y duración suficiente para ese indicador."),
           ({"level": "possible"}, "Método indirecto, señal con reservas o dato orientativo: leer con cautela."),
           ({"level": "insufficient"}, "Registro demasiado corto para ese indicador, o señal no válida.")]
    cw3 = (CW - 28) / 3
    for i, (ev, txt) in enumerate(leg):
        x = M + 14 + i * cw3
        evidence_chip(c, x, Y(top) - 32, ev)
        D.para(c, txt, x, Y(top) - 38, cw3 - 10, F, 7, INK2, leading=8.4, max_h=20)
    top += lh + 10
    bw = (CW - 12) / 2
    need = lambda items, size, gap: sum(D.lines_height(t, bw - 39, F, size) + gap for t in items)
    bh = max(120, min(Y(top) - 54, 52 + max(need(mdl["together"], 7.8, 3.6), need(mdl["limits"], 7.4, 3.0))))
    D.card(c, M, Y(top) - bh, bw, bh, 12)
    section(c, "Interpretar en conjunto", M + 12, top + 8, bw - 24, "chart")
    D.bullets(c, mdl["together"], M + 14, Y(top + 38), bw - 28, 7.8, 3.6, None, max_h=bh - 44)
    x2 = M + bw + 12
    D.card(c, x2, Y(top) - bh, bw, bh, 12)
    section(c, "Limitaciones de esta medición", x2 + 12, top + 8, bw - 24, "alert")
    D.bullets(c, mdl["limits"], x2 + 14, Y(top + 38), bw - 28, 7.4, 3.0, None, max_h=bh - 44)


# ── PÁGINAS 5: plan de acción ───────────────────────────────────────────────────────────────────────────────
def page_plan_a(c, mdl, n, total):
    pl = mdl["plan"]
    frame(c, mdl, "Plan de acción personalizado (1/2)", "Orientación general basada en los resultados de esta medición. Es prudente, no incluye tratamientos ni cambios de medicación.", n, total)
    top, h = 124, 92
    D.gradient_rect(c, M, Y(top) - h, CW, h, [SKY, ICE], "h", r=14)
    D.rrect(c, M, Y(top) - h, CW, h, 14, stroke=LINE)
    D.icon_badge(c, "target", M + 30, Y(top) - 32, 16, HANNA, WHITE)
    D.text(c, "A. OBJETIVO PRINCIPAL", M + 58, Y(top) - 22, FB, 7.6, HANNA)
    D.text(c, pl["focus"][0], M + 58, Y(top) - 39, SSB, 13, DEEP, max_w=CW - 74)
    D.para(c, pl["focus"][1], M + 58, Y(top) - 48, CW - 74, F, 8.4, INK2, leading=10.8, max_h=40)
    t = top + h + 14
    section(c, "B. Estrategia de 7 días", M, t, CW, "calendar")
    t += 30
    cw, ch = (CW - 10) / 2, 100
    for i, card_ in enumerate(pl["weeks"]):
        x = M + (i % 2) * (cw + 10)
        y_top = t + (i // 2) * (ch + 8)
        D.card(c, x, Y(y_top) - ch, cw, ch, 11, fill=(WHITE))
        if card_["priority"]:
            D.rrect(c, x, Y(y_top) - ch, 4, ch, 2, fill=HANNA)
        D.icon_badge(c, card_["icon"], x + 22, Y(y_top) - 22, 11, SKY, HANNA)
        D.text(c, card_["title"], x + 40, Y(y_top) - 25, FSB, 9.6, INK, max_w=cw - 130)
        if card_["priority"]:
            D.chip(c, x + cw - 10, Y(y_top) - 24, "Prioridad", "blue", 6.8, align="r", solid=True)
        D.bullets(c, card_["items"], x + 14, Y(y_top) - 42, cw - 28, 7.7, 2.6, None, max_h=ch - 48)
    t += 3 * (ch + 8) + 6
    D.text(c, "Seguimiento semanal de hábitos", M, Y(t) - 8, FSB, 9.2, INK2)
    t += 16
    lw = 190; dw = (CW - lw) / 7
    D.rrect(c, M, Y(t) - 18, CW, 18, 6, fill=SKY)
    for i, d in enumerate("LMXJVSD"):
        D.text(c, d, M + lw + dw * i + dw / 2, Y(t) - 12.4, FB, 8, DEEP, "c")
    for r_i, hab in enumerate(pl["checklist"]):
        yy = Y(t) - 18 - (r_i + 1) * 17
        D.text(c, hab, M + 8, yy + 5, F, 8, INK, max_w=lw - 14)
        for i in range(7):
            D.rrect(c, M + lw + dw * i + dw / 2 - 5, yy + 2.6, 10, 10, 2.5, stroke=MID, lw=0.9)
        c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(M, yy, M + CW, yy); c.restoreState()
    t += 18 + 5 * 17 + 12
    sy = Y(t) - 12
    nsaf = len(pl["safety"])
    sh = 22 + nsaf * 16 + 4
    D.rrect(c, M, sy - sh, CW, sh, 10, fill=AMBER_T if pl["prof_first"] else ICE, stroke=LINE)
    D.icon(c, "alert" if pl["prof_first"] else "info", M + 12, sy - 22, 14, TONE["amber"][2] if pl["prof_first"] else HANNA)
    D.bullets(c, pl["safety"], M + 34, sy - 9, CW - 46, 7.9, 2.5, ["amber" if pl["prof_first"] else "blue"] * nsaf, max_h=sh - 12)


def page_plan_b(c, mdl, n, total):
    pl = mdl["plan"]
    frame(c, mdl, "Plan de acción personalizado (2/2)", "Seguimiento a 30 días, indicadores a controlar y próxima evaluación.", n, total)
    t = 124
    section(c, "C. Estrategia de 30 días", M, t, CW, "calendar")
    t += 30
    gap = 10; cw = (CW - 3 * gap) / 4; ch = 116
    c.saveState(); c.setStrokeColor(CELESTE); c.setLineWidth(2); c.line(M + cw / 2, Y(t) - 2, M + CW - cw / 2, Y(t) - 2); c.restoreState()
    for i, (wk, ttl, txt) in enumerate(pl["month"]):
        x = M + i * (cw + gap)
        D.dot(c, x + cw / 2, Y(t) - 2, 5, HANNA); D.dot(c, x + cw / 2, Y(t) - 2, 2, WHITE)
        D.card(c, x, Y(t) - 14 - ch, cw, ch, 11)
        D.chip(c, x + 10, Y(t) - 34, wk, "blue", 7.2, solid=True)
        D.para(c, ttl, x + 10, Y(t) - 44, cw - 20, FSB, 9, INK, max_h=24)
        D.para(c, txt, x + 10, Y(t) - 72, cw - 20, F, 7.7, INK2, leading=9.6, max_h=ch - 66)
    t += 14 + ch + 14
    section(c, "D. Indicadores para controlar", M, t, CW, "chart")
    t += 28
    colw = (CW - 10) / 2
    rows = math.ceil(len(pl["control"]) / 2)
    for i, it in enumerate(pl["control"]):
        x = M + (i % 2) * (colw + 10); yy = t + (i // 2) * 24
        D.rrect(c, x, Y(yy) - 20, colw, 20, 7, fill=ICE)
        D.icon(c, "check", x + 8, Y(yy) - 16, 11, HANNA, lw=2.4)
        D.text(c, it, x + 26, Y(yy) - 13.6, F, 8.2, INK, max_w=colw - 34)
    t += rows * 24 + 10
    th = 116
    D.card(c, M, Y(t) - th, CW, th, 12)
    D.icon_badge(c, "clock", M + 22, Y(t) - 22, 11, SKY, HANNA)
    D.text(c, "Cómo estandarizar cada medición", M + 40, Y(t) - 26, FSB, 9.6, INK)
    tips = ["Medir a la misma hora, preferentemente por la mañana, antes de la cafeína.", "Reposar sentado o acostado 3–5 minutos antes de comenzar.",
            "Usar siempre el mismo método y la misma duración.", "Evitar ejercicio intenso, tabaco y alcohol en las horas previas.", "Registrar si hubo mal descanso, estrés o enfermedad ese día."]
    D.bullets(c, tips, M + 16, Y(t) - 40, CW - 32, 7.9, 2.4, None, max_h=th - 46)
    t += th + 14
    eh = 152
    D.gradient_rect(c, M, Y(t) - eh, CW, eh, [DEEP, HANNA, ELECTRIC], "diag", r=16)
    D.icon_badge(c, "calendar", M + 32, Y(t) - 34, 15, D.Color(1, 1, 1, alpha=0.18), WHITE)
    D.text(c, "E. PRÓXIMA EVALUACIÓN SUGERIDA", M + 58, Y(t) - 26, FB, 7.6, CELESTE)
    D.text(c, pl["next"][0], M + 58, Y(t) - 48, SB, 20, WHITE, max_w=CW - 80)
    D.para(c, pl["next"][1], M + 20, Y(t) - 64, CW - 40, F, 8.6, WHITE, leading=11, max_h=40)
    xs = M + 20; cw2 = (CW - 40 - 20) / 3
    D.text(c, "Fechas de referencia contadas desde la generación de este informe", M + 20, Y(t) - eh + 56, F, 7, CELESTE)
    for i, (lab, d) in enumerate([("A 7 días", pl["dates"][0]), ("A 14 días", pl["dates"][1]), ("A 30 días", pl["dates"][2])]):
        x = xs + i * (cw2 + 10)
        D.rrect(c, x, Y(t) - eh + 12, cw2, 32, 9, fill=D.Color(1, 1, 1, alpha=0.16))
        D.text(c, lab, x + 10, Y(t) - eh + 33, FB, 7.2, CELESTE)
        D.text(c, d, x + 10, Y(t) - eh + 19, FSB, 9.6, WHITE)


# ── PÁGINA 6: evolución ─────────────────────────────────────────────────────────────────────────────────────
def page_evolution(c, mdl, n, total):
    ev = mdl["evolution"]
    from .engine import fmt_d
    tz = mdl["tz"]
    if ev["baseline"]:
        frame(c, mdl, "Evolución y seguimiento", "Todavía no hay mediciones anteriores con las que comparar.", n, total)
        top, h = 124, 124
        D.gradient_rect(c, M, Y(top) - h, CW, h, [SKY, ICE], "h", r=16); D.rrect(c, M, Y(top) - h, CW, h, 16, stroke=LINE)
        D.icon_badge(c, "target", M + 36, Y(top) - 40, 20, HANNA, WHITE)
        D.text(c, "Esta medición es su línea base", M + 70, Y(top) - 36, SSB, 14, DEEP)
        D.para(c, "No se muestran tendencias porque solo existe una medición. Los valores de hoy servirán como punto de partida: las próximas mediciones, tomadas en condiciones similares, permitirán observar si los indicadores se mantienen o cambian en el tiempo.", M + 70, Y(top) - 48, CW - 90, F, 8.8, INK2, leading=11.5, max_h=86)
        t = top + h + 16
        section(c, "Qué se podrá comparar", M, t, CW, "chart")
        x, yy = M, Y(t + 36)
        for r in mdl["indicators"]:
            if r["key"] in ("rmssd", "sdnn", "hr_mean", "pnn50", "lf_hf", "lnrmssd"):
                w = D.chip(c, x, yy, f"{r['short']}  {r['text']} {r['unit']}".strip(), "blue", 7.6)
                x += w + 8
        t += 66
        section(c, "Calendario sugerido de seguimiento", M, t, CW, "calendar")
        t += 40
        labs = [("Esta medición", None, "Línea base"), ("A 7 días", None, "Control 1"), ("A 14 días", None, "Control 2"), ("A 30 días", None, "Reevaluación")]
        pl = mdl["plan"]
        ds = [mdl["when"].split(" ")[0], pl["dates"][0], pl["dates"][1], pl["dates"][2]]
        c.saveState(); c.setStrokeColor(CELESTE); c.setLineWidth(2); c.line(M + 50, Y(t), M + CW - 50, Y(t)); c.restoreState()
        for i, (lab, _, name) in enumerate(labs):
            cx = M + 50 + (CW - 100) * i / 3
            D.dot(c, cx, Y(t), 7, HANNA if i == 0 else WHITE); c.saveState(); c.setStrokeColor(HANNA); c.setLineWidth(2); c.circle(cx, Y(t), 7, stroke=1, fill=0); c.restoreState()
            D.text(c, lab, cx, Y(t) - 22, FSB, 9, INK, "c"); D.text(c, ds[i], cx, Y(t) - 34, F, 8, INK3, "c"); D.text(c, name, cx, Y(t) - 46, FB, 7.6, HANNA, "c")
        D.text(c, "Los plazos se cuentan desde la fecha de generación de este informe.", M + CW / 2, Y(t) - 62, F, 7.4, INK3, "c")
        t += 80
        D.card(c, M, Y(t) - 118, CW, 118, 12)
        section(c, "Para que las comparaciones sean válidas", M + 12, t + 8, CW - 24, "info")
        D.bullets(c, ["Mismo método de medición y misma duración en cada control.", "Misma hora del día y misma postura, en reposo.", "Anotar sueño, estrés, cafeína y enfermedad el día de la medición.", "Interpretar la tendencia de varias mediciones, no un valor aislado."], M + 16, Y(t + 38), CW - 32, 8.2, 3.2, None, max_h=72)
        return
    frame(c, mdl, "Evolución y seguimiento", f"Comparación de {ev['n']} mediciones. Se describen los cambios sin atribuirles una causa.", n, total)
    series = ev["series"][:6]
    W2, ch = (CW - 12) / 2, 150
    top = 126
    for i, s in enumerate(series):
        x = M + (i % 2) * (W2 + 12); yt = top + (i // 2) * (ch + 8)
        D.card(c, x, Y(yt) - ch, W2, ch, 12)
        D.text(c, s["name"] + (f" ({s['unit']})" if s["unit"] else ""), x + 14, Y(yt) - 21, FSB, 9.2, INK, max_w=W2 - 110)
        tone = "blue"
        sign = "+" if s["delta"] > 0 else ("−" if s["delta"] < 0 else "")
        lab = f"{sign}{abs(s['delta']):.{s['dec']}f}".replace(".", ",") + (f" ({sign}{abs(s['pct']):.0f} %)" if s["pct"] is not None else "")
        D.chip(c, x + W2 - 12, Y(yt) - 21, "Cambio " + lab, tone, 7, align="r")
        band = ev["rmssd_band"] if s["key"] == "rmssd" else None
        D.line_chart(c, x + 8, Y(yt) - ch + 8, W2 - 16, ch - 40, s["points"], lambda t_: fmt_d(t_, tz), s["dec"], HANNA, band)
    top += math.ceil(len(series) / 2) * (ch + 8) + 2
    D.text(c, "Qué se observa", M, Y(top) - 9, SSB, 10.5, DEEP)
    hgt = D.bullets(c, ev["notes"], M, Y(top + 18), CW, 8, 3, None, max_h=96)
    top += 18 + hgt + 8
    bh = min(Y(top) - 56, 44 + sum(D.lines_height(t_, CW - 39, F, 7.6) + 2.4 for t_ in ev["cautions"]))
    D.rrect(c, M, Y(top) - bh, CW, bh, 12, fill=ICE, stroke=LINE)
    D.icon(c, "info", M + 12, Y(top) - 26, 14, HANNA)
    D.text(c, "Cómo leer estos cambios", M + 34, Y(top) - 21, FSB, 9, INK)
    D.bullets(c, ev["cautions"], M + 14, Y(top) - 32, CW - 28, 7.6, 2.4, None, max_h=bh - 36)
    if ev["rmssd_band"]:
        D.para(c, "La franja verde del gráfico de RMSSD es la referencia del protocolo para la edad y el sexo registrados.", M, 62, CW, F, 6.8, INK3, max_h=12)


# ── PÁGINA FINAL: conclusiones ──────────────────────────────────────────────────────────────────────────────
def page_conclusions(c, mdl, n, total):
    frame(c, mdl, "Conclusiones", "Síntesis de la medición y de los próximos pasos sugeridos.", n, total)
    pl = mdl["plan"]
    t = 124
    section(c, "Principales hallazgos", M, t, CW, "list")
    h = D.bullets(c, [x for _, x in mdl["findings"]], M, Y(t + 28), CW, 8.8, 4, [tone_of(k) for k, _ in mdl["findings"]], max_h=130)
    t += 28 + h + 12
    half = (CW - 12) / 2
    bh = 128
    D.card(c, M, Y(t) - bh, half, bh, 12)
    section(c, "Objetivo prioritario", M + 12, t + 8, half - 24, "target")
    D.text(c, pl["focus"][0], M + 14, Y(t + 40), FSB, 9.4, INK, max_w=half - 28)
    prio = [w["title"] for w in pl["weeks"] if w["priority"]]
    D.para(c, pl["focus"][1], M + 14, Y(t + 48), half - 28, F, 7.9, INK2, leading=9.8, max_h=bh - 78)
    if prio:
        D.text(c, "Hábitos prioritarios: " + ", ".join(prio), M + 14, Y(t) - bh + 10, FB, 7.6, HANNA, max_w=half - 28)
    x2 = M + half + 12
    D.card(c, x2, Y(t) - bh, half, bh, 12)
    section(c, "Seguimiento recomendado", x2 + 12, t + 8, half - 24, "calendar")
    D.text(c, pl["next"][0], x2 + 14, Y(t + 40), SSB, 11, DEEP, max_w=half - 28)
    D.para(c, pl["next"][1], x2 + 14, Y(t + 48), half - 28, F, 7.9, INK2, leading=9.8, max_h=bh - 58)
    D.text(c, "Controlar: " + ", ".join(x.split(" (")[0] for x in pl["control"][:3]), x2 + 14, Y(t) - bh + 10, FB, 7.4, HANNA, max_w=half - 28)
    t += bh + 12
    ih = 70
    D.card(c, M, Y(t) - ih, CW, ih, 12)
    items = [("Fecha de generación", mdl["generated"]), ("N.º de informe", mdl["report_id"]), ("Plataforma", "HBA-HRV"), ("Método", mdl["method"])]
    cw = CW / 4
    for i, (lab, val) in enumerate(items):
        D.text(c, lab, M + 14 + i * cw, Y(t) - 24, FB, 7.2, INK3)
        D.para(c, val, M + 14 + i * cw, Y(t) - 30, cw - 18, FSB, 8.8, INK, max_h=28)
    t += ih + 14
    section(c, "Próximos pasos", M, t, CW, "run")
    t += 28
    steps = [("1", pl["next"][0], "Repetir la medición con las mismas condiciones." if not mdl["plan"]["eval_first"] else "Consultar con un profesional de la salud."),
             ("2", "Durante 7 días", "Aplicar los hábitos del plan y completar el seguimiento semanal."),
             ("3", "A 30 días", "Reevaluar y comparar con esta línea base.")]
    sw = (CW - 20) / 3
    for i, (num_, ttl, txt) in enumerate(steps):
        x = M + i * (sw + 10)
        D.card(c, x, Y(t) - 70, sw, 70, 12)
        D.dot(c, x + 20, Y(t) - 22, 10, HANNA)
        D.text(c, num_, x + 20, Y(t) - 26, SB, 10, WHITE, "c")
        D.text(c, ttl, x + 38, Y(t) - 25, FSB, 8.8, INK, max_w=sw - 48)
        D.para(c, txt, x + 14, Y(t) - 38, sw - 28, F, 7.8, INK2, leading=9.6, max_h=28)
    t += 70 + 14
    D.text(c, "Lecturas de referencia", M, Y(t) - 8, FSB, 8.6, INK2)
    sy = Y(t + 18)
    for s in mdl["sources"]:
        hh = D.para(c, s, M, sy, CW, F, 6.7, INK3, leading=8.2, max_h=22)
        sy -= hh + 2.5
    dh = 64
    D.rrect(c, M, 56, CW, dh, 12, fill=SKY)
    D.icon(c, "shield", M + 14, 56 + dh - 28, 17, HANNA)
    D.text(c, "Nota importante", M + 40, 56 + dh - 20, SSB, 9.4, DEEP)
    D.para(c, mdl["disclaimer"], M + 40, 56 + dh - 26, CW - 56, F, 7.5, INK, leading=9.4, max_h=dh - 30)


# ── armado ───────────────────────────────────────────────────────────────────────────────────────────────────
def plan_pages(mdl):
    inds = mdl["indicators"]
    chunks = [inds[i:i + ROWS_PER_PAGE] for i in range(0, len(inds), ROWS_PER_PAGE)]
    pages = [lambda c, m, n, t: page_cover(c, m, n, t)]
    for i, ch in enumerate(chunks, 1):
        pages.append(lambda c, m, n, t, ch=ch, i=i: page_results(c, m, n, t, ch, i, len(chunks)))
    pages += [page_charts, page_meaning, page_plan_a, page_plan_b, page_evolution, page_conclusions]
    return pages


def build_pdf(mdl):
    D.register_fonts()
    D.WARNINGS.clear()
    pages = plan_pages(mdl)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    c.setTitle("Informe de evaluación HRV")
    c.setAuthor("HBA-HRV")
    c.setSubject("Informe de evaluación HRV")
    c.setCreator("HBA-HRV")
    total = len(pages)
    for i, fn in enumerate(pages, 1):
        fn(c, mdl, i, total)
        c.showPage()
    c.save()
    return buf.getvalue()

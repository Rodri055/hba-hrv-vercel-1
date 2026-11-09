"""
HANNA · hba_report/pdf.py
Informe de 7 páginas (A4). Cada página responde una pregunta del paciente:
  1 ¿Cómo estoy hoy?  2 ¿Qué mide cada cosa y dónde estoy?  3 Mapa RMSSD × FC  4 ¿De dónde salió el número?
  5 Estrés y cargas  6 ¿Qué hago?  7 ¿Cómo vengo?
Todos los gráficos son vectoriales y salen de datos reales; si falta un dato, la sección lo declara.
"""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from . import draw as D
from . import references as R
from .draw import (AMBER, AMBER_T, CELESTE, CYAN, DEEP, ELECTRIC, F, FB, FSB, GREEN, HANNA, ICE, INK, INK2, INK3, LINE,
                   MID, SB, SKY, SSB, TONE, WHITE)

PW, PH = A4
M = 40
CW = PW - 2 * M
FOOT_Y = 36
Y = lambda top: PH - top
BRAND = "HANNA"
FULL = "Heart Anatomy Neuroinmune Network Adaptative"


# ── comunes ─────────────────────────────────────────────────────────────────────────────────────────────────
def footer(c, mdl, n, total):
    c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(M, FOOT_Y + 12, PW - M, FOOT_Y + 12); c.restoreState()
    D.text(c, f"Informe confidencial · generado el {mdl['generated']} · no constituye diagnóstico médico", M, FOOT_Y, F, 6.8, INK3, max_w=CW - 80)
    D.text(c, f"Página {n} de {total}", PW - M, FOOT_Y, FSB, 7.2, INK2, "r")


def frame(c, mdl, title, sub, n, total):
    D.logo_mark(c, M, Y(52), 24)
    D.text(c, BRAND, M + 31, Y(41), SB, 11, DEEP)
    D.text(c, "Informe de evaluación HRV", PW - M, Y(36), FSB, 8, INK3, "r")
    D.text(c, f"Paciente {mdl['patient']['id']}  ·  {mdl['report_id']}", PW - M, Y(47), F, 7.4, INK3, "r", max_w=300)
    c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.7); c.line(M, Y(62), PW - M, Y(62)); c.restoreState()
    D.text(c, title, M, Y(90), SB, 18, DEEP, max_w=CW)
    D.rrect(c, M, Y(98), 30, 3, 1.5, fill=HANNA)
    if sub:
        D.para(c, sub, M, Y(106), CW, F, 8.6, INK3, max_h=24)
    footer(c, mdl, n, total)


def placeholder(c, x, top, w, h, title, msg):
    D.rrect(c, x, Y(top) - h, w, h, 12, fill=ICE, stroke=MID, lw=0.8, dash=([3, 3], 0))
    D.icon(c, "info", x + w / 2 - 9, Y(top) - h / 2 + 4, 18, MID)
    D.text(c, title, x + w / 2, Y(top) - h / 2 - 12, FSB, 8.6, INK2, "c", max_w=w - 20)
    D.para(c, msg, x + 16, Y(top) - h / 2 - 20, w - 32, F, 7.6, INK3, max_h=max(20, h / 2 - 22), align=1)


def card_title(c, x, top, w, title, icon_name):
    D.icon_badge(c, icon_name, x + 17, Y(top) - 19, 9.5, SKY, HANNA)
    D.text(c, title, x + 32, Y(top) - 22.5, FSB, 9.4, INK, max_w=w - 44)


def cap(c, x, y_bottom, w, s, h=26, size=7.2):
    return D.para(c, s, x, y_bottom + h, w, F, size, INK3, leading=size * 1.25, max_h=h)


def tone_state(st):
    return {"green": "green", "amber": "amber", "cyan": "cyan", "red": "red"}.get(st, "blue")


def sensor_conf_line(mdl):
    return f"Confiabilidad del método: {mdl['confidence']}. {mdl['confidence_text']}"


# ── PÁGINA 1 · ¿Cómo estoy hoy? ─────────────────────────────────────────────────────────────────────────────
def page_1(c, mdl, n, total):
    D.gradient_rect(c, 0, Y(196), PW, 196, [DEEP, HANNA, ELECTRIC], "diag")
    c.saveState()
    c.setFillColor(D.Color(1, 1, 1, alpha=0.07)); c.circle(PW - 60, Y(30), 110, stroke=0, fill=1); c.circle(PW - 200, Y(196), 60, stroke=0, fill=1)
    c.setStrokeColor(D.Color(0.66, 0.83, 1, alpha=0.45)); c.setLineWidth(1.8); c.setLineJoin(1)
    p = c.beginPath(); pts = [(410, 96), (448, 96), (462, 78), (478, 116), (492, 88), (502, 96), (PW, 96)]
    p.moveTo(pts[0][0], Y(pts[0][1]))
    for px, py in pts[1:]: p.lineTo(px, Y(py))
    c.drawPath(p, stroke=1, fill=0); c.restoreState()
    D.logo_mark(c, M, Y(62), 30, on_dark=True)
    D.text(c, BRAND, M + 40, Y(47), SB, 16, WHITE)
    D.text(c, FULL, M + 40, Y(59), F, 7.4, CELESTE)
    w = D.tw(mdl["report_id"], FB, 8) + 16
    D.rrect(c, PW - M - w, Y(54), w, 18, 9, stroke=D.Color(1, 1, 1, alpha=0.7), lw=0.9)
    D.text(c, mdl["report_id"], PW - M - w / 2, Y(47.5), FB, 8, WHITE, "c")
    D.text(c, "INFORME DE EVALUACIÓN", M, Y(106), SB, 22, WHITE)
    D.text(c, "DE VARIABILIDAD CARDÍACA", M, Y(132), SB, 22, WHITE)
    D.text(c, f"Medición del {mdl['when']}", M, Y(158), FSB, 10, CELESTE)

    p_, q = mdl["patient"], mdl["quality"]
    top, h = 176, 92
    D.card(c, M, Y(top) - h, CW, h, 14)
    cw = CW / 4
    sex = {"M": "Masculino", "F": "Femenino"}.get(p_["sex"])
    age = f"{p_['age']:g} años" if p_["age"] is not None else "Edad no registrada"
    fields = [("Paciente", p_["id"]), ("Edad y sexo", age + (f" · {sex}" if sex else "")), ("Fecha y hora", mdl["when"]),
              ("Método y duración", mdl["method"].split(" (")[0] + (f" · {mdl['duration']:g} min" if mdl["duration"] else ""))]
    for i, (lab, val) in enumerate(fields):
        x = M + 14 + i * cw
        D.text(c, lab, x, Y(top) - 20, FB, 7, INK3)
        D.text(c, val, x, Y(top) - 34, FSB, 9.2, INK, max_w=cw - 18)
    tone = {"ok": "green", "warn": "amber", "bad": "red", "na": "blue"}[q["level"]]
    yb = Y(top) - 66
    D.text(c, "Calidad de la señal", M + 14, yb + 11, FB, 7, INK3)
    D.chip(c, M + 14, yb - 4, q["label"], tone, 7.6, solid=True)
    D.text(c, q["detail"], M + 14 + D.tw(q["label"], FB, 7.6) + 24, yb - 3.5, F, 7.2, INK3, max_w=cw * 1.6)
    ctx = mdl["patient"]["comorbidities"]
    if ctx:
        D.text(c, "Contexto registrado", M + 14 + 2.2 * cw, yb + 11, FB, 7, INK3)
        D.text(c, ctx, M + 14 + 2.2 * cw, yb - 3.5, FSB, 8, INK, max_w=1.7 * cw)

    t = 290
    D.text(c, "¿Cómo estoy hoy?", M, Y(t) - 14, SB, 15, DEEP)
    D.text(c, "En pocas palabras, un sistema por vez.", M, Y(t) - 28, F, 8.6, INK3)
    t += 38
    for i, b in enumerate(mdl["blocks"]):
        y_top = t + i * 82
        D.card(c, M, Y(y_top) - 74, 296, 74, 11)
        D.rrect(c, M, Y(y_top) - 74, 4.5, 74, 2.2, fill=TONE[tone_state(b["color"])][0])
        D.text(c, b["title"], M + 16, Y(y_top) - 20, FSB, 9.2, INK, max_w=170)
        D.chip(c, M + 288, Y(y_top) - 20, b["label"], tone_state(b["color"]), 7.2, align="r")
        D.para(c, b["text"], M + 16, Y(y_top) - 28, 268, F, 8.2, INK2, leading=10, max_h=28)
        if b.get("pos"):
            D.text(c, b["pos"], M + 16, Y(y_top) - 67, F, 6.9, INK3, max_w=268)
    mx = mdl["matrix"]
    X0 = M + 312
    D.card(c, X0, Y(t) - 238, CW - 312, 238, 12)
    D.text(c, "Mapa RMSSD × frecuencia cardíaca", X0 + 12, Y(t) - 19, FSB, 8.6, INK, max_w=CW - 330)
    if mx["ok"]:
        D.matrix_chart(c, X0 + 52, Y(t) - 186, CW - 312 - 66, 138, mx, mini=True)
        D.text(c, mx["title"], X0 + 12, Y(t) - 214, FSB, 8, DEEP, max_w=CW - 330)
        D.text(c, "Detalle y distancias en la página 3.", X0 + 12, Y(t) - 226, F, 7, INK3)
    else:
        D.para(c, mx["why"], X0 + 12, Y(t) - 70, CW - 336, F, 8, INK3, max_h=120)
    t2 = t + 3 * 82 + 4
    ch = mdl["change"]
    D.rrect(c, M, Y(t2) - 58, CW, 58, 12, fill=ICE, stroke=LINE)
    D.icon(c, "calendar", M + 14, Y(t2) - 34, 16, HANNA)
    if ch and ch.get("rmssd"):
        r = ch["rmssd"]
        D.text(c, "Cambio respecto de la medición anterior", M + 40, Y(t2) - 19, FSB, 8.8, INK)
        msg = (f"El RMSSD pasó de {D.fnum(r['a'])} a {D.fnum(r['b'])} ms ({'+' if r['pct'] > 0 else '−'}{abs(r['pct']):.0f} %)"
               + (f" y la FC de {D.fnum(ch['hr_mean']['a'], 0)} a {D.fnum(ch['hr_mean']['b'], 0)} lpm" if ch.get("hr_mean") else "") + ". "
               + ("" if ch["same_method"] else f"La anterior fue con otro método ({ch['prev_method']}): comparación orientativa. ")
               + "Dos mediciones no constituyen una tendencia.")
        D.para(c, msg, M + 40, Y(t2) - 24, CW - 56, F, 7.8, INK2, leading=9.6, max_h=32)
    else:
        D.text(c, "Primera medición registrada", M + 40, Y(t2) - 19, FSB, 8.8, INK)
        D.para(c, "Esta medición queda como punto de partida: las próximas, hechas en condiciones similares, permitirán ver cómo cambian tus indicadores.", M + 40, Y(t2) - 24, CW - 56, F, 7.8, INK2, leading=9.6, max_h=32)
    t3 = t2 + 68
    D.card(c, M, Y(t3) - 60, CW, 60, 12)
    m_ = mdl["metrics"]
    items = [("Calidad de señal", f"{m_['quality_score']:.0f} %" if m_["quality_score"] is not None else "—"),
             ("Artefactos", f"{D.fnum(m_['artifact_percent'], 1)} %" if m_["artifact_percent"] is not None else "—"),
             ("Latidos analizados", f"{m_['n_nn']:.0f}" if m_["n_nn"] is not None else (str(mdl["beats"]["n"]) if mdl["beats"] else "—")),
             ("Duración", f"{mdl['duration']:g} min" if mdl["duration"] else "—")]
    for i, (lab, val) in enumerate(items):
        x = M + 14 + i * (CW - 28) / 4
        D.text(c, lab, x, Y(t3) - 19, FB, 7, INK3)
        D.text(c, val, x, Y(t3) - 38, SB, 13, INK)
    if m_["quality_score"] is not None:
        D.quality_bar(c, M + 14, Y(t3) - 54, CW - 28, 5, m_["quality_score"])
    D.para(c, "Este informe describe los resultados de una medición fisiológica y ofrece orientación general. No es un diagnóstico médico.", M, Y(t3 + 72), CW, F, 7.6, INK3, max_h=12)
    footer(c, mdl, n, total)


# ── PÁGINA 2 · ¿Qué mide cada cosa y dónde estoy? ───────────────────────────────────────────────────────────
def page_2(c, mdl, n, total):
    frame(c, mdl, "¿Qué mide cada cosa y dónde estoy?", "Qué hace cada grupo en el cuerpo y dónde estás hoy respecto del rango de referencia del protocolo HANNA.", n, total)
    top = 128
    LW, ROWH = 148, 46
    for g in mdl["groups"]:
        n_rows = len(g["rows"])
        hwhat = D.lines_height(g["what"], LW - 14, F, 7.3, 9.1)
        body = max(48 + hwhat, n_rows * ROWH + 4)
        gh = body + 30
        D.card(c, M, Y(top) - gh, CW, gh, 12)
        D.rrect(c, M, Y(top) - gh, LW, gh, 12, fill=ICE)
        D.icon_badge(c, g["icon"], M + 20, Y(top) - 20, 10, SKY, HANNA)
        D.para(c, g["title"], M + 36, Y(top) - 10, LW - 42, SSB, 8.2, DEEP, leading=9.8, max_h=21)
        D.text(c, g["sub"], M + 10, Y(top) - 44, F, 6.8, INK3, max_w=LW - 14)
        D.para(c, g["what"], M + 10, Y(top) - 50, LW - 14, F, 7.3, INK2, leading=9.1, max_h=body - 48)
        rx = M + LW + 10
        for i, r in enumerate(g["rows"]):
            ry = top + 4 + i * ROWH
            if i:
                c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.5); c.line(rx, Y(ry), M + CW - 10, Y(ry)); c.restoreState()
            D.text(c, r["short"], rx, Y(ry) - 14, FSB, 8.4, INK, max_w=84)
            D.text(c, r["text"], rx, Y(ry) - 33, SB, 14, INK, max_w=70)
            if r["unit"]:
                D.text(c, r["unit"], rx + D.tw(r["text"], SB, 14) + 3, Y(ry) - 33, FSB, 7.4, INK3)
            bx = rx + 88
            if r["scale"]:
                D.position_bar(c, bx, Y(ry) - 14, 92, r["value"], r["band"], r["attn"], r["scale"][0], r["scale"][1])
                D.para(c, r["pos"], bx, Y(ry) - 27, 92, FSB, 6.6, TONE[tone_state(r["color"])][2], leading=7.8, max_h=17)
            else:
                D.para(c, r["pos"], bx, Y(ry) - 12, 92, F, 6.8, INK3, leading=8, max_h=30)
            mtxt = r["meaning"] + (f" ({r['caveat']})" if r["caveat"] else "")
            D.para(c, mtxt, bx + 100, Y(ry) - 7, CW - LW - 10 - 88 - 100 - 10, F, 7, INK, leading=8.4, max_h=ROWH - 6)
        sy = Y(top) - gh + 4
        D.para(c, f"<b>{g['fav_label']}</b> {g['fav']}   <b>{g['red_label']}</b> {g['red']}", rx, sy + 24, CW - LW - 20, F, 6.9, INK3, leading=8.2, max_h=22, markup=True)
        top += gh + 8
    comp = mdl["complements"]
    if comp:
        ch_ = 66
        D.text(c, "Indicadores complementarios", M, Y(top) - 9, FSB, 8.6, INK2)
        top += 14
        tw_ = (CW - (len(comp) - 1) * 8) / len(comp)
        for i, (nm, val, unit, desc) in enumerate(comp):
            x = M + i * (tw_ + 8)
            D.card(c, x, Y(top) - ch_, tw_, ch_, 10)
            D.text(c, nm, x + 10, Y(top) - 15, FB, 7.2, INK3)
            D.text(c, val, x + 10, Y(top) - 31, SB, 12, INK)
            if unit:
                D.text(c, unit, x + 12 + D.tw(val, SB, 12), Y(top) - 31, FSB, 7.2, INK3)
            D.para(c, desc, x + 10, Y(top) - 36, tw_ - 18, F, 6.6, INK3, leading=7.8, max_h=27)


# ── PÁGINA 3 · Mapa RMSSD × FC ──────────────────────────────────────────────────────────────────────────────
def page_3(c, mdl, n, total):
    frame(c, mdl, "Tu mapa RMSSD × frecuencia cardíaca", "Combina dos datos de tu medición para ubicarla respecto de los límites del protocolo. Es una lectura descriptiva, no un diagnóstico.", n, total)
    mx = mdl["matrix"]
    if not mx["ok"]:
        placeholder(c, M, 130, CW, 300, "Mapa no disponible", mx["why"])
        return
    D.card(c, M, Y(128) - 342, CW, 342, 14)
    D.matrix_chart(c, M + 92, Y(128) - 312, CW - 92 - 22, 280, mx)
    top = 484
    half = (CW - 12) / 2
    D.card(c, M, Y(top) - 130, half, 130, 12)
    D.text(c, "Tu ubicación", M + 14, Y(top) - 19, FSB, 9, INK2)
    D.chip(c, M + 14, Y(top) - 38, mx["title"], "blue", 8, solid=True)
    hh_ = D.para(c, mx["text"], M + 14, Y(top) - 48, half - 28, F, 8.2, INK, leading=10.2, max_h=62)
    if mx.get("near"):
        nm = mx["near"]
        msg_ = (f"Tu {nm[0]} está muy cerca del límite" if len(nm) == 1 else "Tu RMSSD y tu frecuencia cardíaca están muy cerca de sus límites") + ": una pequeña variación podría cambiarte de celda."
        D.para(c, msg_, M + 14, Y(top) - 52 - hh_, half - 28, FSB, 7.2, DEEP, leading=8.8, max_h=26)
    x2 = M + half + 12
    D.card(c, x2, Y(top) - 130, half, 130, 12)
    D.text(c, "Distancia a los límites del protocolo", x2 + 14, Y(top) - 19, FSB, 9, INK2)
    D.text(c, "RMSSD", x2 + 14, Y(top) - 40, FB, 7.4, INK3)
    D.para(c, mx["rmssd"]["txt"][0].upper() + mx["rmssd"]["txt"][1:], x2 + 14, Y(top) - 44, half - 28, FSB, 8.2, INK, leading=10, max_h=24)
    D.text(c, "Frecuencia cardíaca", x2 + 14, Y(top) - 76, FB, 7.4, INK3)
    D.para(c, mx["hr"]["txt"][0].upper() + mx["hr"]["txt"][1:], x2 + 14, Y(top) - 80, half - 28, FSB, 8.2, INK, leading=10, max_h=24)
    D.para(c, "Las líneas punteadas del mapa muestran estas distancias.", x2 + 14, Y(top) - 112, half - 28, F, 7, INK3, max_h=12)
    top2 = top + 142
    D.rrect(c, M, Y(top2) - 118, CW, 118, 12, fill=ICE, stroke=LINE)
    D.icon(c, "info", M + 14, Y(top2) - 30, 15, HANNA)
    D.text(c, "Qué puede influir en estos dos valores", M + 38, Y(top2) - 24, FSB, 9, INK)
    D.para(c, "Tanto el RMSSD como la frecuencia cardíaca cambian con: " + mdl["influence"], M + 38, Y(top2) - 32, CW - 54, F, 8, INK2, leading=10, max_h=40)
    D.text(c, "Cómo leer el mapa", M + 38, Y(top2) - 78, FSB, 8.4, INK)
    D.para(c, "Las columnas y filas tienen igual ancho; dentro de cada una, el punto está en su posición proporcional. La celda verde es la combinación de referencia (ambos valores dentro de su rango). Los límites son los del protocolo HANNA, no una norma poblacional." + (" Como no se registró la edad, el rango de RMSSD es el general." if mdl["patient"]["age"] is None else ""), M + 38, Y(top2) - 84, CW - 54, F, 7.5, INK3, leading=9.2, max_h=30)


# ── PÁGINA 4 · ¿De dónde salió el número? ───────────────────────────────────────────────────────────────────
def page_4(c, mdl, n, total):
    frame(c, mdl, "¿De dónde salió el número?", "Cada punto es el intervalo entre dos latidos reales de tu medición. De esos intervalos se calculan todos los indicadores.", n, total)
    bt = mdl["beats"]
    t = 128
    if bt:
        D.card(c, M, Y(t) - 246, CW, 246, 12)
        card_title(c, M, t, CW, "Tus latidos durante la medición", "pulse")
        x = M + CW - 14
        for lab, tone in [("sobre 85 lpm", "amber"), ("60–85 lpm", "green"), ("bajo 60 lpm", "cyan")]:
            wch = D.chip(c, x, Y(t) - 20, lab, tone, 6.8, align="r"); x -= wch + 5
        D.tacogram(c, M + 8, Y(t) - 216, CW - 16, 172, bt)
        p = bt["pct"]
        D.text(c, f"{bt['inside']} de {bt['n']} latidos ({p[1]:.0f} %) dentro de 60–85 lpm  ·  {p[0]:.0f} % bajo 60 lpm  ·  {p[2]:.0f} % sobre 85 lpm", M + 14, Y(t) - 229, FB, 7.8, INK)
        cap(c, M + 14, Y(t) - 244, CW - 28, "Cuanto más alto el punto, más lento latía el corazón en ese momento (eje derecho: latidos por minuto).", 11, 7)
    else:
        placeholder(c, M, t, CW, 246, "Gráfico de latidos no disponible", "Se muestra en el informe generado el día de la medición. Las sesiones guardadas conservan los indicadores, no la serie de latidos.")
    t2 = t + 256
    wl = 300
    D.card(c, M, Y(t2) - 184, wl, 184, 12)
    if mdl["ppg_view"]:
        card_title(c, M, t2, wl, "Señal capturada y latidos detectados", "heart")
        D.ppg_trace(c, M + 8, Y(t2) - 150, wl - 16, 106, mdl["ppg_view"])
        cap(c, M + 14, Y(t2) - 180, wl - 28, "Pulso óptico capturado y filtrado (no es un ECG). Los círculos marcan los latidos detectados; el número es el tiempo entre latidos, en ms.", 28)
    elif bt:
        card_title(c, M, t2, wl, "Tren de latidos (12 s)", "heart")
        D.beat_train(c, M + 8, Y(t2) - 150, wl - 16, 106, bt)
        cap(c, M + 14, Y(t2) - 180, wl - 28, "Cada marca es un latido registrado; el número es el tiempo entre latidos, en ms. No es un ECG: el sensor entrega solo los intervalos.", 28)
    else:
        placeholder(c, M, t2, wl, 184, "Señal no disponible", "No hay serie de latidos ni señal capturada en esta medición.")
    x2 = M + wl + 12
    w2 = CW - wl - 12
    if bt:
        D.card(c, x2, Y(t2) - 184, w2, 184, 12)
        card_title(c, x2, t2, w2, "Distribución de intervalos", "chart")
        D.histogram(c, x2 + 8, Y(t2) - 150, w2 - 16, 106, bt["nn"], 12)
        cap(c, x2 + 14, Y(t2) - 180, w2 - 28, "Una distribución más ancha indica más variación entre un latido y otro.", 28)
    else:
        placeholder(c, x2, t2, w2, 184, "Histograma no disponible", "Requiere la serie de latidos.")
    t3 = t2 + 194
    D.card(c, M, Y(t3) - 112, CW, 112, 12)
    card_title(c, M, t3, CW, "Calidad de la medición", "shield")
    m_ = mdl["metrics"]
    q = m_["quality_score"]
    if q is not None:
        D.quality_bar(c, M + 14, Y(t3) - 46, CW - 28, 8, q)
        D.text(c, f"{q:.0f} % de calidad de señal" + (f"  ·  {D.fnum(m_['artifact_percent'], 1)} % de artefactos" if m_["artifact_percent"] is not None else ""), M + 14, Y(t3) - 62, FSB, 8.6, INK)
    else:
        D.text(c, "Este método no entregó un índice de calidad de señal.", M + 14, Y(t3) - 52, FSB, 8.6, INK)
    D.para(c, "Los latidos con artefactos (por movimiento o mala detección) se corrigen o se excluyen antes de calcular los indicadores. " + sensor_conf_line(mdl), M + 14, Y(t3) - 72, CW - 28, F, 7.8, INK2, leading=9.6, max_h=34)
    D.text(c, f"Método: {mdl['method']}" + (f"  ·  {mdl['duration']:g} min" if mdl["duration"] else ""), M + 14, Y(t3) - 100, F, 7.4, INK3, max_w=CW - 28)


# ── PÁGINA 5 · Estrés y cargas ──────────────────────────────────────────────────────────────────────────────
def page_5(c, mdl, n, total):
    frame(c, mdl, "Estrés y cargas", "Dos formas de ver cómo se reparte la carga del organismo. Son estimaciones del modelo HANNA, no mediciones directas.", n, total)
    t = 128
    wl = (CW - 12) / 2
    bt, m_, L = mdl["beats"], mdl["metrics"], mdl["loads"]
    D.card(c, M, Y(t) - 300, wl, 300, 12)
    if bt and m_["sd1"] and m_["sd2"] and not L["invalid"]:
        card_title(c, M, t, wl, "Poincaré: cada latido frente al siguiente", "target")
        D.poincare(c, M + 8, Y(t) - 250, 218, bt["nn"], m_["sd1"], m_["sd2"])
        D.text(c, f"SD1 {D.fnum(m_['sd1'])} ms · SD2 {D.fnum(m_['sd2'])} ms", M + 14, Y(t) - 262, FB, 8, INK)
        cap(c, M + 14, Y(t) - 297, wl - 28, "SD1 (ancho de la nube) refleja la variación de corto plazo; SD2 (largo), la lenta.", 24, 6.9)
    else:
        placeholder(c, M, t, wl, 300, "Poincaré no disponible", "Requiere la serie de latidos y una señal válida (se muestra en el informe del día de la medición).")
    x2 = M + wl + 12
    D.card(c, x2, Y(t) - 300, wl, 300, 12)
    if L["map_ok"] and not L["invalid"]:
        card_title(c, x2, t, wl, "Mapa carga física × emocional", "chart")
        D.loads_map(c, x2 + 8, Y(t) - 250, 218, L["phys"]["value"], L["emo"]["value"], L["auto"]["value"], L["stress"])
        st = L["stress"]
        D.text(c, f"Tamaño: carga autonómica {L['auto']['value']:.0f}" + (f"  ·  Anillo: estrés {st['level']}" if st and st.get("level") else ""), x2 + 14, Y(t) - 262, FB, 7.6, INK, max_w=wl - 28)
        cap(c, x2 + 14, Y(t) - 297, wl - 28, "Líneas punteadas en 25 y 55, los cortes de nivel del modelo. Más arriba y a la derecha, mayor carga.", 24, 6.9)
    else:
        placeholder(c, x2, t, wl, 300, "Mapa de cargas no disponible", "Faltan índices de carga o la señal no es válida.")
    t2 = t + 312
    D.card(c, M, Y(t2) - 188, CW, 188, 12)
    card_title(c, M, t2, CW, "Distribución de las cargas (0–100)", "list")
    if L["items"] and not L["invalid"]:
        for i, (_, lab, v) in enumerate(L["items"]):
            yy = t2 + 40 + i * 25
            D.text(c, lab, M + 14, Y(yy), FSB, 8.2, INK2)
            D.text(c, f"{v['value']:.0f}" + (f" · {v['level']}" if v["level"] else ""), M + CW - 14, Y(yy), SB, 8.6, INK, "r")
            D.hbar_levels(c, M + 14, Y(yy) - 12, CW - 28, v["value"])
        yy = t2 + 40 + len(L["items"]) * 25
        if L["stype_txt"]:
            D.text(c, f"Lectura del modelo: {L['stype_txt'].lower()}.", M + 14, Y(yy) - 2, FSB, 8, DEEP)
    else:
        D.para(c, "Esta medición no incluye índices de carga o su señal no es válida.", M + 14, Y(t2 + 44), CW - 28, F, 8.4, INK3, max_h=30)
    D.text(c, "Los cortes blancos de las barras marcan los niveles 25 · 55 · 78 (bajo, moderado, alto, muy alto).", M + 14, Y(t2) - 180, F, 6.8, INK3, max_w=CW - 28)
    t3 = t2 + 200
    D.rrect(c, M, Y(t3) - 70, CW, 70, 12, fill=ICE, stroke=LINE)
    D.icon(c, "info", M + 14, Y(t3) - 28, 15, HANNA)
    D.text(c, "Cómo leer estas cargas", M + 38, Y(t3) - 22, FSB, 8.8, INK)
    D.para(c, "Son estimaciones compuestas que calcula el modelo HANNA a partir de varios indicadores (comparten RMSSD y LF/HF, por eso no son independientes). No miden emociones ni actividad autonómica de forma directa, y no sustituyen la evaluación de un profesional.", M + 38, Y(t3) - 28, CW - 54, F, 7.6, INK2, leading=9.4, max_h=38)


# ── PÁGINA 6 · ¿Qué hago? ───────────────────────────────────────────────────────────────────────────────────
def page_6(c, mdl, n, total):
    pl = mdl["plan"]
    frame(c, mdl, "¿Qué hago?", "Orientación general y prudente según esta medición. No incluye tratamientos ni cambios de medicación.", n, total)
    top, h = 126, 72
    D.gradient_rect(c, M, Y(top) - h, CW, h, [SKY, ICE], "h", r=14)
    D.rrect(c, M, Y(top) - h, CW, h, 14, stroke=LINE)
    D.icon_badge(c, "target", M + 28, Y(top) - 28, 14, HANNA, WHITE)
    D.text(c, "OBJETIVO SUGERIDO", M + 52, Y(top) - 19, FB, 7, HANNA)
    D.text(c, pl["focus"][0], M + 52, Y(top) - 34, SSB, 11.5, DEEP, max_w=CW - 66)
    D.para(c, pl["focus"][1], M + 52, Y(top) - 40, CW - 66, F, 7.8, INK2, leading=9.6, max_h=28)
    t = top + h + 12
    D.text(c, "Para los próximos 7 días", M, Y(t) - 10, SSB, 10.5, DEEP)
    t += 18
    cw, chh = (CW - 10) / 2, 82
    for i, k in enumerate(pl["weeks"][:4]):
        x = M + (i % 2) * (cw + 10); yt = t + (i // 2) * (chh + 8)
        D.card(c, x, Y(yt) - chh, cw, chh, 11)
        if k["priority"]:
            D.rrect(c, x, Y(yt) - chh, 4, chh, 2, fill=HANNA)
        D.icon_badge(c, k["icon"], x + 22, Y(yt) - 21, 10.5, SKY, HANNA)
        D.text(c, k["title"], x + 40, Y(yt) - 24, FSB, 9.2, INK, max_w=cw - 120)
        if k["priority"]:
            D.chip(c, x + cw - 10, Y(yt) - 23, "Prioridad", "blue", 6.6, align="r", solid=True)
        D.bullets(c, k["items"], x + 14, Y(yt) - 38, cw - 28, 7.5, 2.2, None, max_h=chh - 42)
    t += 2 * (chh + 8) + 2
    D.text(c, "Seguimiento semanal", M, Y(t) - 8, FSB, 8.8, INK2)
    t += 14
    lw = 180; dw = (CW - lw) / 7
    D.rrect(c, M, Y(t) - 16, CW, 16, 6, fill=SKY)
    for i, d in enumerate("LMXJVSD"):
        D.text(c, d, M + lw + dw * i + dw / 2, Y(t) - 11, FB, 7.6, DEEP, "c")
    for r_i, hab in enumerate(pl["checklist"]):
        yy = Y(t) - 16 - (r_i + 1) * 15
        D.text(c, hab, M + 8, yy + 4.5, F, 7.6, INK, max_w=lw - 12)
        for i in range(7):
            D.rrect(c, M + lw + dw * i + dw / 2 - 4.5, yy + 2.4, 9, 9, 2.2, stroke=MID, lw=0.8)
        c.saveState(); c.setStrokeColor(LINE); c.setLineWidth(0.4); c.line(M, yy, M + CW, yy); c.restoreState()
    t += 16 + len(pl["checklist"]) * 15 + 10
    half = (CW - 12) / 2
    bh = 138
    D.card(c, M, Y(t) - bh, half, bh, 12)
    D.icon_badge(c, "calendar", M + 20, Y(t) - 20, 9.5, SKY, HANNA)
    D.text(c, "Qué volver a medir y cuándo", M + 36, Y(t) - 23, FSB, 9, INK)
    D.text(c, pl["next"][0], M + 14, Y(t) - 46, SSB, 12, DEEP, max_w=half - 28)
    D.para(c, pl["next"][1], M + 14, Y(t) - 52, half - 28, F, 7.4, INK2, leading=9, max_h=36)
    D.para(c, "Controlar: " + "; ".join(x.split(" (")[0] for x in pl["control"][:4]) + ".", M + 14, Y(t) - 92, half - 28, FB, 7.2, HANNA, leading=8.8, max_h=28)
    D.para(c, "A los 30 días: reevaluar y comparar con esta medición.", M + 14, Y(t) - 122, half - 28, F, 7.2, INK3, max_h=12)
    x2 = M + half + 12
    D.card(c, x2, Y(t) - bh, half, bh, 12)
    D.icon_badge(c, "clock", x2 + 20, Y(t) - 20, 9.5, SKY, HANNA)
    D.text(c, "Cómo medir para poder comparar", x2 + 36, Y(t) - 23, FSB, 9, INK)
    tips = ["Misma hora, mejor por la mañana y antes de la cafeína.", "Reposar 3–5 minutos sentado o acostado antes.", "Mismo método y misma duración.",
            "Evitar ejercicio intenso, tabaco y alcohol en las horas previas.", "Anotar si hubo mal descanso, estrés o enfermedad."]
    D.bullets(c, tips, x2 + 14, Y(t) - 36, half - 28, 7.3, 2.0, None, max_h=bh - 42)
    t += bh + 10
    sh = 70
    D.rrect(c, M, Y(t) - sh, CW, sh, 12, fill=AMBER_T, stroke=LINE)
    D.icon(c, "alert", M + 14, Y(t) - 28, 15, TONE["amber"][2])
    D.text(c, "Consultá a un profesional de la salud si aparece alguno de estos síntomas", M + 38, Y(t) - 20, FSB, 8.4, INK)
    D.para(c, "Dolor o presión en el pecho · mareos intensos o desmayos · palpitaciones intensas o irregulares · falta de aire inusual · frecuencia en reposo persistentemente menor a 40 o mayor a 100 lpm con síntomas. " + " ".join(pl["safety"]), M + 38, Y(t) - 26, CW - 54, F, 7.4, INK2, leading=9, max_h=40)


# ── PÁGINA 7 · ¿Cómo vengo? ─────────────────────────────────────────────────────────────────────────────────
def page_7(c, mdl, n, total):
    from .engine import fmt_d
    ev, tz = mdl["evolution"], mdl["tz"]
    frame(c, mdl, "¿Cómo vengo?", "Comparación con mediciones anteriores y conclusiones.", n, total)
    t = 126
    pts = ev.get("pts", [])
    ser = {s["key"]: s for s in ev["series"]}
    half = (CW - 12) / 2
    if "rmssd" in ser or "hr_mean" in ser:
        sens = sorted({p["sensor"] for p in pts if p.get("sensor") and p.get("rmssd") is not None})
        for i, (key, title, unit, dec) in enumerate([("rmssd", "RMSSD", "ms", 1), ("hr_mean", "Frecuencia cardíaca", "lpm", 0)]):
            x = M + i * (half + 12)
            D.card(c, x, Y(t) - 212, half, 212, 12)
            D.text(c, f"{title} ({unit})", x + 14, Y(t) - 21, FSB, 9, INK, max_w=half - 130)
            s = ser.get(key)
            if not s:
                placeholder(c, x + 10, t + 34, half - 20, 150, "Sin datos suficientes", "No hay al menos dos mediciones con este indicador.")
                continue
            sign = "+" if s["delta"] > 0 else ("−" if s["delta"] < 0 else "")
            lab = f"{sign}{abs(s['delta']):.{dec}f}".replace(".", ",") + (f" ({sign}{abs(s['pct']):.0f} %)" if s["pct"] is not None else "")
            D.chip(c, x + half - 12, Y(t) - 21, "Cambio " + lab, "blue", 6.8, align="r")
            data = [(p["ts"], p[key], p.get("sensor")) for p in pts if p.get(key) is not None]
            D.evo_chart(c, x + 6, Y(t) - 186, half - 12, 150, data, lambda d: fmt_d(d, tz), dec, HANNA, ev["rmssd_band"] if key == "rmssd" else None)
            D.text(c, "La franja verde es el rango del protocolo para tu edad y sexo." if key == "rmssd" and ev["rmssd_band"] else "Escala propia para cada gráfico.", x + 14, Y(t) - 205, F, 6.6, INK3, max_w=half - 28)
        t += 222
        notes = []
        if ev["mixed_methods"]:
            notes.append(("amber", "Se comparan mediciones hechas con métodos distintos (" + ", ".join(ev["methods"]) + "): la comparación es orientativa."))
        if ev["mixed_dur"]:
            notes.append(("amber", "Las mediciones tuvieron duraciones distintas, lo que afecta a SDNN y a los indicadores espectrales."))
        notes.append(("blue", "Dos mediciones permiten comparar, pero no constituyen una tendencia. Los cambios entre días pueden deberse a muchos factores." if ev["n"] < 3 else "Los cambios se describen sin atribuirles una causa: sueño, estrés, cafeína, hora y postura pueden influir."))
        hh = 14 + sum(D.lines_height(s, CW - 52, F, 7.6, 9.2) + 3 for _, s in notes)
        D.rrect(c, M, Y(t) - hh, CW, hh, 10, fill=ICE, stroke=LINE)
        yy = Y(t) - 9
        for tone, s in notes:
            h_ = D.para(c, s, M + 36, yy, CW - 52, F, 7.6, INK2, leading=9.2, max_h=30)
            D.dot(c, M + 20, yy - 6, 3, TONE[tone][0]); yy -= h_ + 3
        x_ = M + CW - 14
        for sn in reversed(sens):
            lab = R.SENSOR_LABEL[sn].split(" (")[0]
            x_ -= D.tw(lab, F, 6.6) + 14
        t += hh + 12
    else:
        D.gradient_rect(c, M, Y(t) - 112, CW, 112, [SKY, ICE], "h", r=16); D.rrect(c, M, Y(t) - 112, CW, 112, 16, stroke=LINE)
        D.icon_badge(c, "target", M + 36, Y(t) - 38, 19, HANNA, WHITE)
        D.text(c, "Esta medición es tu punto de partida", M + 68, Y(t) - 36, SSB, 13, DEEP)
        D.para(c, "No hay mediciones anteriores con las que comparar, por eso no se muestran gráficos de evolución. Las próximas mediciones, hechas con el mismo método, la misma duración y en condiciones parecidas, permitirán ver cómo cambian el RMSSD y la frecuencia cardíaca.", M + 68, Y(t) - 46, CW - 88, F, 8.4, INK2, leading=10.6, max_h=56)
        t += 126
    ch_ = 128
    D.card(c, M, Y(t) - ch_, CW, ch_, 12)
    D.icon_badge(c, "list", M + 20, Y(t) - 20, 9.5, SKY, HANNA)
    D.text(c, "Conclusiones", M + 36, Y(t) - 24, SSB, 10.4, DEEP)
    D.bullets(c, mdl["conclusions"], M + 16, Y(t) - 38, CW - 32, 8, 3.6, None, max_h=ch_ - 44)
    t += ch_ + 10
    dh = 60
    D.rrect(c, M, Y(t) - dh, CW, dh, 12, fill=SKY)
    D.icon(c, "shield", M + 14, Y(t) - 26, 16, HANNA)
    D.text(c, "Nota importante", M + 40, Y(t) - 20, SSB, 9, DEEP)
    D.para(c, mdl["disclaimer"], M + 40, Y(t) - 26, CW - 56, F, 7.1, INK, leading=8.6, max_h=dh - 28)
    t += dh + 8
    D.text(c, "Lecturas de referencia", M, Y(t) - 8, FSB, 7.8, INK2)
    sy = Y(t + 14)
    for s in mdl["sources"]:
        hh = D.para(c, s, M, sy, CW, F, 6.3, INK3, leading=7.6, max_h=18); sy -= hh + 1.5


# ── armado ───────────────────────────────────────────────────────────────────────────────────────────────────
def build_pdf(mdl):
    D.register_fonts()
    D.WARNINGS.clear()
    pages = [page_1, page_2, page_3, page_4, page_5, page_6, page_7]
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    c.setTitle("Informe de evaluación HRV")
    c.setAuthor(BRAND)
    c.setSubject("Informe de evaluación HRV")
    c.setCreator(BRAND)
    total = len(pages)
    for i, fn in enumerate(pages, 1):
        fn(c, mdl, i, total)
        c.showPage()
    c.save()
    return buf.getvalue()

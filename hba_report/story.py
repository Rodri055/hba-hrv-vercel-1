"""
HANNA · hba_report/story.py
Contenido explicativo y datos derivados para el informe de 7 páginas.
- Los textos "qué es / qué significa" son FIJOS (revisables una sola vez); lo único que cambia es dónde está la persona.
- Todo número sale de datos reales. Si falta algo, la sección lo declara.
- Lenguaje descriptivo: nunca diagnostica ni prescribe tratamientos.
"""
import math

from . import references as R

DEC = {"rmssd": 1, "hr_mean": 0, "sdnn": 1, "sd1": 1, "sd2": 1, "dfa_alpha1": 2, "lf_hf": 2, "baevsky": 0}
RM_ES = {"low": "bajo", "in": "en rango", "high": "alto"}
FC_ES = {"low": "baja", "in": "en rango", "high": "alta"}


def es(v, d=1):
    return "—" if v is None else f"{v:.{d}f}".replace(".", ",")


# ── textos fijos por indicador y estado ─────────────────────────────────────────────────────────────────────
MEANING = {
    "rmssd": {
        "low": "Tu freno vagal está menos ágil de lo esperado para tu edad: el cuerpo tarda más en volver a la calma después de un estrés.",
        "in": "Tu freno vagal responde con agilidad, dentro de lo esperado para tu edad: buena capacidad de volver a la calma tras una exigencia.",
        "high": "Tu freno vagal es muy ágil, por encima de lo esperado para tu edad. Suele acompañar a una buena recuperación; si el valor es muy alto, conviene confirmar que no haya artefactos.",
    },
    "pnn50": {"none": "Porcentaje de latidos que cambian más de 50 ms respecto del anterior. Cuanto mayor, más ágil es el freno vagal. El protocolo no define un rango para este indicador."},
    "sd1": {
        "low": "La variación de corto plazo es baja: va en línea con un freno vagal menos ágil.",
        "in": "La variación de corto plazo está en rango y acompaña al RMSSD.",
        "high": "La variación de corto plazo supera el rango y acompaña a un RMSSD alto.",
    },
    "hr_mean": {
        "low": "Tu corazón late más lento que el rango de reposo del protocolo: el freno vagal domina. Es habitual en personas entrenadas; si aparecen mareos o desmayos, conviene consultarlo.",
        "in": "Tu frecuencia está dentro del rango de reposo del protocolo: hay equilibrio entre el freno y el acelerador.",
        "high": "Tu frecuencia está por encima del rango de reposo: pueden estar pesando el acelerador o factores del momento como cafeína, calor, dolor o nerviosismo. Conviene repetir en reposo.",
    },
    "baevsky": {
        "low": "Índice de tensión bajo: el sistema necesita poco esfuerzo para mantenerse regulado.",
        "in": "Tensión reguladora dentro del rango.",
        "high": "Índice de tensión alto: el sistema está haciendo más esfuerzo para mantener el equilibrio.",
    },
    "lf_hf": {
        "low": "Mayor peso relativo de la banda HF (vagal). No es una medición directa del equilibrio simpático-vagal.",
        "in": "Dentro del rango. No es una medición directa del equilibrio simpático-vagal.",
        "high": "Mayor peso relativo de la banda LF; puede reflejar activación, pero también influyen la respiración y la postura. No es una medición directa del equilibrio simpático-vagal.",
    },
    "sdnn": {
        "low": "La variabilidad total es baja para un registro corto: menos margen de adaptación en este registro.",
        "in": "Margen de adaptación dentro del rango.",
        "high": "Margen de adaptación amplio, por encima del rango. Es informativo.",
    },
    "sd2": {
        "low": "La variación lenta es baja: menor margen para adaptarse a cambios graduales.",
        "in": "La variación lenta está dentro del rango.",
        "high": "La variación lenta supera el rango: amplio margen de adaptación. Es informativo.",
    },
    "dfa_alpha1": {
        "low": "Menor complejidad: la regulación del ritmo es más rígida.",
        "in": "Regulación con complejidad saludable (cerca de 1).",
        "high": "Valor por encima del rango; conviene confirmar que no haya errores de detección de latidos.",
    },
}

GROUPS = [
    dict(id="vagal", title="Freno vagal", sub="Sistema parasimpático", icon="heart", keys=["rmssd", "pnn50", "sd1"],
         what=("El nervio vago es la rama parasimpática del sistema nervioso autónomo. Llega directo al marcapasos del corazón y funciona como "
               "un freno: mantiene el latido más lento y lo ajusta latido a latido, sin que lo decidas. Cuanto más ágil es ese freno, mejor se "
               "adapta el cuerpo a una exigencia y más rápido vuelve a la calma. Estos indicadores miden esa agilidad."),
         fav="sueño suficiente, ejercicio aeróbico regular, respiración lenta, descanso.",
         red="estrés sostenido, falta de sueño, alcohol, dolor, infecciones, sobreentrenamiento."),
    dict(id="activ", title="Activación y frecuencia cardíaca", sub="Freno y acelerador", icon="pulse", keys=["hr_mean", "baevsky", "lf_hf"],
         what=("La frecuencia cardíaca resulta de dos fuerzas: el freno vagal, que la baja, y el acelerador simpático (adrenalina), que la sube. "
               "En reposo, un valor bajo indica que domina el freno; uno alto, que el acelerador o factores del momento pesan más. "
               "Ningún indicador de HRV mide por sí solo la actividad simpática."),
         fav_label="Bajan la activación:", fav="descanso, entrenamiento aeróbico, relajación, respiración lenta.",
         red_label="Suben la activación:", red="estrés, cafeína, calor, deshidratación, dolor, fiebre, ejercicio reciente."),
    dict(id="reserva", title="Reserva global y complejidad", sub="Margen de adaptación", icon="chart", keys=["sdnn", "sd2", "dfa_alpha1"],
         what=("Estos indicadores miran el margen total que tiene el corazón para variar su ritmo, no solo de un latido al siguiente sino también "
               "en oscilaciones más lentas (respiración, presión, temperatura). Más reserva significa más capacidad de adaptarse a cambios. "
               "El DFA alfa-1 describe si esa variación tiene un orden saludable (cerca de 1) o se vuelve rígida o desordenada."),
         fav="actividad física regular, buen descanso, hábitos estables.",
         red="fatiga acumulada, estrés prolongado, sedentarismo, enfermedad."),
]

SHORT_ST = {  # frase corta por sistema para la portada
    "vagal": {"low": ("Menos ágil", "Menos ágil de lo esperado para tu edad: el cuerpo tarda más en recuperarse de un estrés."),
              "in": ("Ágil", "Responde con agilidad, dentro de lo esperado para tu edad: buena capacidad de volver a la calma."),
              "high": ("Muy ágil", "Muy ágil, por encima de lo esperado para tu edad.")},
    "activ": {"low": ("Baja", "Corazón en reposo profundo: el freno vagal domina sobre el acelerador."),
              "in": ("En equilibrio", "Freno y acelerador equilibrados, dentro del rango de reposo."),
              "high": ("Alta", "Más activado de lo habitual en reposo; cafeína, calor, dolor o nerviosismo pueden influir.")},
    "reserva": {"low": ("Reducida", "Margen de adaptación reducido en este registro."),
                "in": ("En rango", "Margen de adaptación dentro del rango."),
                "high": ("Amplia", "Margen de adaptación amplio, por encima del rango.")},
}
KEY_OF = {"vagal": "rmssd", "activ": "hr_mean", "reserva": "sdnn"}

# ── mapa RMSSD × FC: lectura descriptiva de cada celda (columna RMSSD, fila FC) ───────────────────────────
CELLS = {
    ("low", "high"): "Variabilidad por debajo y frecuencia por encima del rango. Esta combinación se observa con mayor activación del organismo (por ejemplo tras mal descanso, estrés, dolor, cafeína, calor o ante una enfermedad en curso). Una sola medición no permite saber cuál es el motivo.",
    ("low", "in"): "Variabilidad por debajo del rango con frecuencia de reposo normal. Puede acompañar a períodos de cansancio o de carga sostenida, o ser una variación del día. Conviene repetir y observar si se mantiene.",
    ("low", "low"): "Variabilidad por debajo y frecuencia también por debajo del rango. Es una combinación poco intuitiva: se ha descrito en personas muy entrenadas con fatiga acumulada, con ciertos medicamentos que reducen la frecuencia y por errores de detección. Conviene confirmar la calidad de la señal y repetir.",
    ("in", "high"): "Variabilidad dentro del rango con frecuencia por encima del rango de reposo. Suele estar influida por factores del momento: cafeína, calor, hidratación, postura, nerviosismo o actividad previa. Conviene repetir tras unos minutos de reposo.",
    ("in", "in"): "Variabilidad y frecuencia dentro del rango del protocolo: es la combinación de referencia.",
    ("in", "low"): "Variabilidad dentro del rango y frecuencia baja en reposo: habitual en personas con buen acondicionamiento físico o en un reposo profundo.",
    ("high", "high"): "Combinación infrecuente. Antes de interpretarla conviene descartar artefactos, latidos extra o respiración muy irregular, y repetir la medición.",
    ("high", "in"): "Variabilidad por encima del rango con frecuencia normal: freno vagal muy ágil. Es habitual en personas jóvenes o entrenadas.",
    ("high", "low"): "Variabilidad alta con frecuencia baja en reposo: patrón frecuente en personas entrenadas y con buena recuperación en reposo.",
}
INFLUENCE = ("sueño, cafeína, hidratación, postura, respiración, estrés, dolor, medicamentos, hora del día y actividad reciente. "
             "Ningún indicador aislado permite concluir fatiga, enfermedad o estrés emocional.")

LEVEL_TXT = {"bajo": "bajo", "moderado": "moderado", "alto": "alto", "muy alto": "muy alto"}
STRESS_TXT = {
    "fisico": "Predominio de carga física", "fisico_leve": "Leve predominio de carga física",
    "emocional": "Predominio de carga emocional", "emocional_leve": "Leve predominio de carga emocional",
    "equilibrado": "Cargas equilibradas",
}


def _cls(v, lo, hi):
    return "low" if v < lo else ("high" if v > hi else "in")


def position_text(r):
    if r["state"] == "invalid":
        return "No interpretable"
    if r["band"] is None:
        return "Sin rango de referencia en el protocolo"
    d, u = DEC.get(r["key"], 1), r["unit"]
    f = lambda x: es(x, d) + (f" {u}" if u else "")
    lo, hi = r["band"]
    v = r["value"]
    if v < lo:
        return f"{f(lo - v)} por debajo del límite inferior"
    if v > hi:
        return f"{f(v - hi)} por encima del límite superior"
    dlo, dhi = v - lo, hi - v
    return f"Dentro del rango, a {f(min(dlo, dhi))} del límite {'inferior' if dlo <= dhi else 'superior'}"


def bar_scale(r):
    lo, hi = r["band"]
    w = hi - lo
    vmin, vmax = max(0.0, lo - 0.8 * w), hi + 0.8 * w
    span = vmax - vmin
    return min(vmin, r["value"] - 0.08 * span), max(vmax, r["value"] + 0.08 * span)


def caveat(key, dur):
    if dur is None:
        return None
    if key == "lf_hf" and dur < 5:
        return "Registro menor a 5 min: valor orientativo."
    if key in ("sdnn", "sd2", "dfa_alpha1", "baevsky") and dur < 3:
        return "Registro corto: valor orientativo."
    return None


def build_groups(model):
    byk = {r["key"]: r for r in model["indicators"]}
    invalid = model["alerts"]["severity"] == "invalid"
    dur = model["duration"]
    out = []
    for g in GROUPS:
        rows = []
        for k in g["keys"]:
            r = byk.get(k)
            if not r:
                continue
            txt = MEANING.get(k, {})
            if invalid:
                meaning = "No interpretable: la señal presenta inconsistencias técnicas."
            else:
                meaning = txt.get(r["state"], txt.get("none", ""))
            rows.append({"key": k, "name": r["name"], "short": r["short"], "value": r["value"], "text": r["text"], "unit": r["unit"],
                         "band": r["band"], "color": r["color"], "state": r["state"], "pos": position_text(r), "meaning": meaning,
                         "caveat": caveat(k, dur), "scale": bar_scale(r) if (r["band"] and not invalid) else None,
                         "attn": R.INDICATORS[k]["attn"], "extra": r["extra"]})
        if rows:
            out.append({**{k: g[k] for k in ("id", "title", "sub", "icon", "what", "fav", "red")}, "fav_label": g.get("fav_label", "Lo favorecen:"), "red_label": g.get("red_label", "Lo reducen:"), "rows": rows})
    return out


def build_complements(model):
    byk = {r["key"]: r for r in model["indicators"]}
    out = []
    r = byk.get("lnrmssd")
    if r:
        out.append(("lnRMSSD", r["text"], "", "Versión logarítmica del RMSSD, útil para comparar mediciones."))
    r = byk.get("mean_rr")
    if r:
        hr = f" (aprox. {es(60000 / r['value'], 0)} lpm)" if r["value"] else ""
        out.append(("RR medio", r["text"], "ms", "Tiempo promedio entre latidos" + hr + "."))
    r = byk.get("sd1_sd2_ratio")
    if r:
        out.append(("SD1/SD2", r["text"], "", "Proporción entre la variación corta y la lenta."))
    r = byk.get("hf_share")
    if r:
        out.append(("HF relativo", r["text"], "%", "Parte de la potencia (HF+LF) que es HF." + (" Orientativo (< 5 min)." if (model["duration"] or 0) < 5 else "")))
    return out


# ── mapa RMSSD × FC ─────────────────────────────────────────────────────────────────────────────────────────
def build_matrix(model):
    byk = {r["key"]: r for r in model["indicators"]}
    rm, hr = byk.get("rmssd"), byk.get("hr_mean")
    if model["alerts"]["severity"] == "invalid":
        return {"ok": False, "why": "La señal presenta inconsistencias técnicas: no se ubica la medición en el mapa."}
    if not rm or not hr or not rm["band"] or not hr["band"]:
        return {"ok": False, "why": "Faltan el RMSSD o la frecuencia cardíaca en esta medición."}
    xc = _cls(rm["value"], *rm["band"])
    yc = _cls(hr["value"], *hr["band"])
    def side(r):
        lo, hi = r["band"]
        v = r["value"]
        d = DEC[r["key"]]
        u = r["unit"]
        if v < lo:
            return f"{es(lo - v, d)} {u} por debajo del límite inferior ({es(lo, 0)} {u})"
        if v > hi:
            return f"{es(v - hi, d)} {u} por encima del límite superior ({es(hi, 0)} {u})"
        dlo, dhi = v - lo, hi - v
        near = "inferior" if dlo <= dhi else "superior"
        return f"dentro del rango, a {es(min(dlo, dhi), d)} {u} del límite {near} ({es(lo if dlo <= dhi else hi, 0)} {u})"
    def near(r):
        lo, hi = r["band"]; v = r["value"]
        dist = (lo - v) if v < lo else ((v - hi) if v > hi else min(v - lo, hi - v))
        return dist <= 0.08 * (hi - lo)
    nr = [n for n, r in (("RMSSD", rm), ("frecuencia cardíaca", hr)) if near(r)]
    return {"ok": True, "x": xc, "y": yc, "text": CELLS[(xc, yc)], "near": nr,
            "title": f"RMSSD {RM_ES[xc]} · FC {FC_ES[yc]}",
            "rmssd": {"v": rm["value"], "lo": rm["band"][0], "hi": rm["band"][1], "txt": side(rm)},
            "hr": {"v": hr["value"], "lo": hr["band"][0], "hi": hr["band"][1], "txt": side(hr)}}


# ── latidos / señal ─────────────────────────────────────────────────────────────────────────────────────────
def build_beats(model):
    nn = model["metrics"].get("nn_ms") or []
    if len(nn) < 12:
        return None
    hr = [60000.0 / v for v in nn]
    n = len(nn)
    below = sum(1 for h in hr if h < 60)
    above = sum(1 for h in hr if h > 85)
    inside = n - below - above
    t, acc = [], 0.0
    for v in nn:
        acc += v / 1000.0
        t.append(acc)
    # ventana de 12 s más regular (para el tren de latidos)
    best, bs = 0, None
    for i in range(0, n - 6):
        j = i
        while j < n and t[j] - t[i] <= 12.0:
            j += 1
        seg = nn[i:j]
        if len(seg) < 6:
            continue
        mean = sum(seg) / len(seg)
        sd = math.sqrt(sum((x - mean) ** 2 for x in seg) / len(seg))
        sc = sd / mean
        if bs is None or sc < bs:
            best, bs = i, sc
    j = best
    while j < n and t[j] - t[best] <= 12.0:
        j += 1
    return {"nn": nn, "t": t, "n": n, "below": below, "inside": inside, "above": above,
            "pct": [100.0 * below / n, 100.0 * inside / n, 100.0 * above / n], "win": (best, j)}


# ── cambio respecto de la medición anterior ────────────────────────────────────────────────────────────────
def build_change(model):
    ev = model["evolution"]
    pts = [p for p in ev.get("pts", []) if p.get("rmssd") is not None]
    if model["alerts"]["severity"] == "invalid" or len(pts) < 2:
        return None
    cur, prev = pts[-1], pts[-2]
    ch = {"prev_ts": prev["ts"], "same_method": cur["sensor"] == prev["sensor"], "prev_method": R.SENSOR_LABEL.get(prev["sensor"], "método no registrado"),
          "n": len(pts)}
    for k in ("rmssd", "hr_mean"):
        a, b = prev.get(k), cur.get(k)
        if a is not None and b is not None and a:
            ch[k] = {"a": a, "b": b, "d": b - a, "pct": (b - a) / a * 100.0}
    return ch


# ── cargas HANNA ────────────────────────────────────────────────────────────────────────────────────────────
def build_loads(model):
    c = {k: v for k, _, v in model["cargas"]}
    ph, em, au, st = (c.get("carga_fisica"), c.get("carga_emocional"), c.get("carga_autonomica"), c.get("estres"))
    map_ok = bool(ph and em and au)
    stype = model.get("stress_type")
    return {"map_ok": map_ok, "phys": ph, "emo": em, "auto": au, "stress": st, "items": model["cargas"],
            "stype_txt": STRESS_TXT.get(stype), "invalid": model["alerts"]["severity"] == "invalid"}


# ── resumen de portada y conclusiones ──────────────────────────────────────────────────────────────────────
def build_blocks(model, groups):
    out = []
    for g in groups:
        r = next((x for x in g["rows"] if x["key"] == KEY_OF[g["id"]]), None)
        if not r and g["id"] == "reserva":
            r = next((x for x in g["rows"] if x["state"] in ("low", "in", "high")), None)
        if not r or r["state"] not in ("low", "in", "high") or model["alerts"]["severity"] == "invalid":
            out.append({"id": g["id"], "title": g["title"], "label": "Sin datos", "text": "No hay datos suficientes o la señal no es válida para valorar este sistema.", "color": "blue"})
            continue
        lab, txt = SHORT_ST[g["id"]][r["state"]]
        out.append({"id": g["id"], "title": g["title"], "label": lab, "text": txt, "color": r["color"], "pos": f"{r['short']}: {r['pos']}"})
    return out


def build_conclusions(model, matrix, change, blocks):
    inval = model["alerts"]["severity"] == "invalid"
    out = []
    if inval:
        out.append("La señal de esta medición presenta inconsistencias técnicas, por lo que los valores no se interpretan. Conviene repetirla siguiendo las indicaciones de preparación.")
    else:
        out.append(" · ".join(f"{b['title']}: {b['label'].lower()}" for b in blocks) + ".")
        if matrix.get("ok"):
            out.append(f"En el mapa HRV × frecuencia cardíaca, la medición cae en «{matrix['title']}». {matrix['text']}")
    if change:
        r = change.get("rmssd")
        if r:
            out.append(f"Respecto de la medición anterior, el RMSSD pasó de {es(r['a'])} a {es(r['b'])} ms ({'+' if r['pct'] > 0 else '−'}{abs(r['pct']):.0f} %)."
                       + ("" if change["same_method"] else " Fueron métodos distintos, por lo que la comparación es orientativa.")
                       + " Dos mediciones no constituyen una tendencia.")
    if model["patient"]["age"] is None:
        out.append("No se registró la edad: el RMSSD se ubicó con el rango general (25–55 ms), que es menos preciso.")
    nxt = model["plan"]["next"]
    out.append(f"Próxima evaluación sugerida: {nxt[0].lower()}, en las mismas condiciones.")
    return out


def enrich(model):
    groups = build_groups(model)
    matrix = build_matrix(model)
    change = build_change(model)
    blocks = build_blocks(model, groups)
    model.update({"groups": groups, "complements": build_complements(model), "matrix": matrix, "beats": build_beats(model),
                  "ppg_view": model["metrics"].get("ppg_view"), "change": change, "loads": build_loads(model), "blocks": blocks,
                  "influence": INFLUENCE})
    model["conclusions"] = build_conclusions(model, matrix, change, blocks)
    return model

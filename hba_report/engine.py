"""
HBA-HRV · report/engine.py
Motor de interpretación. Recibe resultados REALES y devuelve un "modelo de informe" (dict) con todo lo que el
generador de PDF necesita. No calcula HRV ni dibuja: separa la lógica clínica de la presentación.

Reglas de oro
- Nunca se inventan valores: si un indicador no está, no aparece.
- Nunca se emite un diagnóstico; el lenguaje es siempre prudente.
- Las explicaciones se generan por reglas (determinísticas) sobre los datos recibidos. No se usa IA generativa.
"""
import hashlib
import math
import os
import sys
from datetime import datetime, timedelta, timezone

from . import references as R

try:
    from hrv_core import rmssd_reference
except ImportError:  # el paquete puede importarse sin que /api esté en sys.path
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api"))
    from hrv_core import rmssd_reference

NUM_KEYS = ["hr_mean", "hr_min", "hr_max", "rmssd", "rmssd_corr", "lnrmssd", "sdnn", "mean_rr", "pnn50", "lf_power",
            "hf_power", "total_power", "lf_hf", "sd1", "sd2", "sd1_sd2_ratio", "dfa_alpha1", "baevsky",
            "resp_rate_rpm", "artifact_percent", "quality_score", "duration_minutes", "n_nn", "duration_correction"]

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


# ── utilidades ─────────────────────────────────────────────────────────────────────────────────────────────
def num(v):
    try:
        if v is None or v == "" or isinstance(v, bool):
            return None
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def es(v, dec=1):
    """Número con coma decimal."""
    if v is None:
        return "—"
    return f"{v:.{dec}f}".replace(".", ",")


def clip(s, n):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def parse_ts(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def local(d, tz_min):
    return d.astimezone(timezone(timedelta(minutes=tz_min)))


def fmt_dt(d, tz_min):
    d = local(d, tz_min)
    return f"{d.day:02d}/{d.month:02d}/{d.year} {d.hour:02d}:{d.minute:02d}"


def fmt_d(d, tz_min):
    d = local(d, tz_min)
    return f"{d.day} {MONTHS[d.month - 1]}"


# ── normalización de métricas (resultado de /api/compute o fila guardada del historial) ──────────────────────
def normalize_metrics(m):
    m = m or {}
    out = {k: num(m.get(k)) for k in NUM_KEYS}
    out["sensor_type"] = m.get("sensor_type") if m.get("sensor_type") in R.SENSOR_LABEL else None
    dash = m.get("hba_dashboard") or {}
    cargas_src = dash.get("cargas") or {}
    out["cargas"] = {}
    for key, _ in R.CARGAS:
        v = num((cargas_src.get(key) or {}).get("value")) if cargas_src else None
        if v is None:
            v = num(m.get(key))
        lvl = (cargas_src.get(key) or {}).get("level") if cargas_src else None
        if v is not None:
            out["cargas"][key] = {"value": v, "level": lvl}
    sem = dash.get("semaphore") or {}
    out["semaphore_label"] = sem.get("label") or m.get("semaphore_label")
    out["stress_type"] = dash.get("stress_type") or m.get("stress_type")
    out["freq_warning"] = m.get("freq_warning") or None
    out["rmssd_main"] = out["rmssd_corr"] if out["rmssd_corr"] is not None else out["rmssd"]
    lf, hf = out["lf_power"], out["hf_power"]
    # Las potencias absolutas no se informan (su unidad no está verificada); se usa el reparto relativo.
    out["hf_share"] = hf / (lf + hf) * 100 if lf is not None and hf is not None and lf >= 0 and hf >= 0 and lf + hf > 0 else None
    return out


# ── validez técnica (espejo de static/js/hrv_validator.js) ──────────────────────────────────────────────────
def technical_alerts(m):
    V, issues, sev = R.VALIDITY, [], "ok"

    def add(level, field, msg):
        nonlocal sev
        issues.append({"level": level, "field": field, "msg": msg})
        if level == "invalid":
            sev = "invalid"
        elif sev == "ok":
            sev = "warn"

    r, hr, art, q = m["rmssd_main"], m["hr_mean"], m["artifact_percent"], m["quality_score"]
    if r is not None:
        T = V["rmssd"]
        if r < T["floor_hard"]:
            add("invalid", "RMSSD", "Señal plana: probable falta de contacto con el sensor o artefacto total.")
        elif r < T["floor_warn"]:
            add("warn", "RMSSD", "Señal extremadamente débil: verificar el contacto con el sensor.")
        elif r > T["ceil_hard"]:
            add("invalid", "RMSSD", "Valor fisiológicamente imposible: artefacto severo o señal corrupta.")
        elif r > T["ceil_warn"]:
            add("warn", "RMSSD", "Valor extremadamente alto: verificar si es correcto.")
    if hr is not None:
        T = V["hr"]
        if hr < T["floor_hard"] or hr > T["ceil_hard"]:
            add("invalid", "FC media", "Frecuencia cardíaca imposible: artefacto de señal.")
        elif hr < T["floor_warn"] or hr > T["ceil_warn"]:
            add("warn", "FC media", "Frecuencia cardíaca extrema: verificar el contacto del sensor.")
    if art is not None:
        T = V["artifacts"]
        if art > T["hard"]:
            add("invalid", "Artefactos", f"{es(art, 1)} % de artefactos: los resultados no son confiables.")
        elif art > T["bad"]:
            add("warn", "Artefactos", f"{es(art, 1)} % de artefactos: interpretar con precaución.")
        elif art > T["warn"]:
            add("warn", "Artefactos", f"{es(art, 1)} % de artefactos: la señal tuvo cierta inestabilidad.")
    if q is not None and q < V["quality"]["bad"]:
        add("warn", "Calidad de señal", f"{es(q, 0)} %: insuficiente.")
    return {"severity": sev, "issues": issues}


def signal_quality(m, alerts):
    """Etiqueta de calidad global basada en datos reales (o 'sin dato')."""
    q, art = m["quality_score"], m["artifact_percent"]
    if alerts["severity"] == "invalid":
        return {"label": "No válida", "level": "bad", "detail": "Se detectaron inconsistencias técnicas."}
    if q is None and art is None:
        return {"label": "Sin dato de calidad", "level": "na", "detail": "El método no entregó un índice de calidad."}
    ok = (q is None or q >= R.VALIDITY["quality"]["warn"]) and (art is None or art <= R.VALIDITY["artifacts"]["warn"])
    if ok:
        return {"label": "Adecuada", "level": "ok", "detail": "Sin alertas técnicas relevantes."}
    return {"label": "Con reservas", "level": "warn", "detail": "Hay indicios de ruido; interpretar con precaución."}


# ── clasificación por indicador ────────────────────────────────────────────────────────────────────────────
def band_for(key, age, sex):
    spec = R.INDICATORS[key]
    if spec["band"] is None:
        return None
    if spec["band"] == "age_sex":
        lo, hi = rmssd_reference(age, sex)
        return (lo, hi)
    return spec["band"]


def band_text(key, band, age_known):
    if band is None:
        return None
    spec = R.INDICATORS[key]
    g = lambda x: ("%g" % round(x, 2)).replace(".", ",")
    t = f"{g(band[0])}–{g(band[1])}" + (f" {spec['unit']}" if spec["unit"] else "")
    if key == "rmssd" and not age_known:
        t += " (referencia general: edad no registrada)"
    return t


def evidence(key, value, conf, qual_level, dur):
    if value is None:
        return None
    if qual_level == "bad":
        return {"level": "insufficient", "reason": "La señal no es válida."}
    mn = R.INDICATORS[key]["min_min"]
    if dur is not None and dur + 1e-9 < mn:
        return {"level": "insufficient", "reason": f"Se recomienda un registro de al menos {mn} min para este indicador (se midió {es(dur, 0)} min)."}
    if conf == "alta" and qual_level in ("ok", "na"):
        return {"level": "solid", "reason": "Método directo y señal sin alertas." if qual_level == "ok" else "Método directo; sin índice de calidad."}
    reasons = []
    if conf != "alta":
        reasons.append("método " + conf)
    if qual_level == "warn":
        reasons.append("señal con reservas")
    return {"level": "possible", "reason": "Interpretar con cautela: " + " y ".join(reasons) + "."}


def build_indicators(m, age, sex, conf, qual_level, dur, invalid=False):
    age_known = age is not None
    rows = []
    for key in R.ORDER:
        spec = R.INDICATORS[key]
        value = m["rmssd_main"] if key == "rmssd" else m.get(key)
        if value is None:
            continue
        band = band_for(key, age, sex)
        state, color, side = "none", "blue", None
        if band is not None:
            if value < band[0]:
                state, side = "low", "low"
            elif value > band[1]:
                state, side = "high", "high"
            else:
                state = "in"
            color = "green" if state == "in" else ("amber" if side == spec["attn"] else "cyan")
        bt = band_text(key, band, age_known)
        txt_key = state if state in spec["meaning"] else "none"
        meaning = spec["meaning"].get(txt_key, "")
        meaning = meaning.replace("{band}", bt or "")
        extra = None
        if key == "rmssd" and m["rmssd"] is not None and m["rmssd_corr"] is not None:
            f = m["duration_correction"]
            extra = f"Sin corregir: {es(m['rmssd'], 1)} ms" + (f" · factor por duración ×{es(f, 2)}" if f else "")
        if key == "hf_share":
            extra = f"HF {es(value, 0)} % · LF {es(100 - value, 0)} %"
        if key == "hr_mean" and m["hr_min"] is not None and m["hr_max"] is not None:
            extra = f"Mín–máx durante el registro: {es(m['hr_min'], 0)}–{es(m['hr_max'], 0)} bpm"
        if invalid:
            state, color, bt = "invalid", "red", None
            meaning = "Valor no interpretable: la señal presenta inconsistencias técnicas."
        rows.append({
            "key": key, "name": spec["name"], "short": spec["short"], "unit": spec["unit"], "dec": spec["dec"],
            "value": value, "text": es(value, spec["dec"]), "band": band, "band_text": bt, "state": state, "color": color,
            "measures": spec["measures"], "meaning": meaning,
            "follow": "Repetir la medición siguiendo las indicaciones de preparación." if invalid else spec["follow"], "extra": extra,
            "evidence": evidence(key, value, conf, qual_level, dur),
        })
    return rows


# ── cuerpo del informe ────────────────────────────────────────────────────────────────────────────────────
def sensor_conf(sensor):
    return R.SENSOR_CONFIDENCE.get(sensor, ("moderada", "Método sin clasificar."))


def findings(ind, alerts, quality, m, dur, age):
    out = []
    byk = {r["key"]: r for r in ind}
    if alerts["severity"] == "invalid":
        out.append(("alert", "Se detectaron inconsistencias técnicas en la señal: conviene repetir la medición antes de interpretar los valores."))
    else:
        q, a = m["quality_score"], m["artifact_percent"]
        parts = []
        if q is not None:
            parts.append(f"calidad de señal {es(q, 0)} %")
        if a is not None:
            parts.append(f"{es(a, 1)} % de artefactos")
        out.append(("ok" if quality["level"] == "ok" else ("attn" if quality["level"] == "warn" else "info"),
                    "La señal registrada tuvo " + " y ".join(parts) + "." if parts else "No se dispone de un índice de calidad de señal para este método."))
    r = byk.get("rmssd")
    if r and r["band_text"] and alerts["severity"] != "invalid":
        if r["state"] == "in":
            out.append(("ok", f"El RMSSD ({r['text']} ms) se ubica dentro de la referencia del protocolo para su perfil."))
        elif r["state"] == "low":
            out.append(("attn", f"El RMSSD ({r['text']} ms) está por debajo de la referencia del protocolo para su perfil: es un indicador a seguir."))
        else:
            out.append(("info", f"El RMSSD ({r['text']} ms) está por encima de la referencia del protocolo para su perfil."))
    h = byk.get("hr_mean")
    if h and alerts["severity"] != "invalid":
        if h["state"] == "in":
            out.append(("ok", f"La frecuencia cardíaca media ({h['text']} bpm) está dentro de la banda del protocolo."))
        elif h["state"] == "high":
            out.append(("attn", f"La frecuencia cardíaca media ({h['text']} bpm) es superior a 85 bpm; conviene repetir en reposo."))
        else:
            out.append(("info", f"La frecuencia cardíaca media ({h['text']} bpm) es inferior a 60 bpm; puede ser habitual con buen acondicionamiento."))
    s = byk.get("sdnn")
    if s and s["evidence"] and s["evidence"]["level"] != "insufficient" and alerts["severity"] != "invalid" and len(out) < 4:
        out.append(("ok" if s["state"] == "in" else "info", f"La variabilidad global (SDNN {s['text']} ms) " + ("está dentro de la banda del protocolo." if s["state"] == "in" else "está fuera de la banda del protocolo; se interpreta junto con el RMSSD.")))
    return out[:4]


def summary_text(ind, alerts, m, dur, method_label, when, age, sex):
    s = [f"Esta evaluación se realizó el {when} con {method_label}" + (f", con un registro de {es(dur, 0)} min." if dur else ".")]
    byk = {r["key"]: r for r in ind}
    if alerts["severity"] == "invalid":
        s.append("Los valores presentan inconsistencias técnicas, por lo que no se interpretan. Se recomienda repetir la medición en condiciones estandarizadas.")
        return " ".join(s)
    r = byk.get("rmssd")
    if r:
        pos = {"in": "dentro de", "low": "por debajo de", "high": "por encima de"}[r["state"]]
        s.append(f"El indicador principal de variabilidad vagal (RMSSD) fue de {r['text']} ms y se ubica {pos} la referencia del protocolo para su perfil ({r['band_text']}).")
    h = byk.get("hr_mean")
    if h:
        s.append(f"La frecuencia cardíaca media fue de {h['text']} bpm.")
    if alerts["severity"] == "warn":
        s.append("Hubo advertencias técnicas en la señal, por lo que conviene interpretar con cautela.")
    if age is None:
        s.append("No se registró la edad, por lo que se usó una referencia general para el RMSSD.")
    s.append("Un resultado aislado describe un momento puntual: su valor principal está en compararlo con mediciones futuras tomadas en condiciones similares.")
    return " ".join(s)


def interpretation_rows(ind):
    pri = ["rmssd", "hr_mean", "sdnn", "lf_hf", "dfa_alpha1", "baevsky", "sd1", "pnn50"]
    byk = {r["key"]: r for r in ind}
    rows = []
    for k in pri:
        r = byk.get(k)
        if not r:
            continue
        obs = f"{r['name']}: {r['text']}" + (f" {r['unit']}" if r["unit"] else "")
        obs += f". Referencia: {r['band_text']}." if r["band_text"] else ". Sin referencia definida en el protocolo."
        attn = r["color"] == "amber"
        follow = ("Indicador a seguir en próximas mediciones. " if attn else "") + r["follow"]
        rows.append({"key": k, "name": r["name"], "observed": obs, "meaning": r["meaning"], "follow": follow, "evidence": r["evidence"], "color": r["color"]})
        if len(rows) == 4:
            break
    return rows


def together_notes(ind, dur):
    if ind and ind[0]["state"] == "invalid":
        return ["Con una señal no válida no corresponde interpretar los indicadores en conjunto."]
    byk = {r["key"]: r for r in ind}
    g = lambda k: byk[k]["state"] if k in byk else None
    notes = []
    if g("rmssd") == "low" and g("hr_mean") == "high":
        notes.append("RMSSD por debajo de la referencia junto con frecuencia cardíaca elevada es un patrón que el protocolo asocia a estrés o fatiga; no es concluyente por sí solo.")
    if g("rmssd") == "low" and g("dfa_alpha1") == "low":
        notes.append("RMSSD bajo con DFA alfa-1 bajo: el protocolo lo vincula a fatiga física acumulada. Requiere confirmar con mediciones repetidas.")
    if g("rmssd") == "low" and g("dfa_alpha1") == "in" and g("lf_hf") == "high":
        notes.append("RMSSD bajo con DFA alfa-1 en rango y LF/HF elevado: el protocolo lo vincula a carga emocional. LF/HF requiere registros de 5 min o más.")
    inb = [r for r in ind if r["state"] in ("in", "low", "high")]
    if inb and all(r["state"] == "in" for r in inb) and len(inb) >= 2:
        notes.append("Los indicadores con referencia disponibles son coherentes entre sí y se ubican dentro de sus bandas.")
    if not notes:
        notes.append("Se interpretan en conjunto el RMSSD (modulación vagal), el SDNN (variabilidad global), la frecuencia cardíaca y, con registros de 5 min o más, la relación LF/HF.")
    return notes[:3]


def limitations(ind, m, dur, conf, conf_txt, age, n_hist, alerts=None):
    out = []
    for i in (alerts or {}).get("issues", [])[:2]:
        out.append(f"Alerta técnica ({i['field']}): {i['msg']}")
    out.append(f"Confiabilidad del método: {conf}. {conf_txt}")
    if dur is not None and dur < 5:
        out.append(f"El registro fue de {es(dur, 0)} min. El análisis espectral (LF, HF, LF/HF) requiere unos 5 min; esos valores son orientativos.")
    if n_hist == 0:
        out.append("Es una única medición: describe un momento puntual y está influida por sueño, cafeína, estrés, postura y hora del día.")
    if age is None:
        out.append("Sin edad registrada, la referencia del RMSSD es general y menos precisa.")
    out.append("Las bandas de referencia son umbrales operativos del protocolo HBA, no normas poblacionales; no existe un rango universal.")
    have = {r["key"] for r in ind}
    miss = [R.INDICATORS[k]["short"] for k in ("sdnn", "lf_hf", "pnn50", "dfa_alpha1", "baevsky") if k not in have]
    if miss:
        out.append("No se dispone de: " + ", ".join(miss) + " (no calculados con este método o registro).")
    return out[:6]


# ── plan de acción ────────────────────────────────────────────────────────────────────────────────────────
def build_plan(ind, alerts, quality, m, dur, conf, age, comorb, n_hist, now_local):
    byk = {r["key"]: r for r in ind}
    st = lambda k: byk[k]["state"] if k in byk else None
    hr = m["hr_mean"]
    invalid = alerts["severity"] == "invalid"
    poor = invalid or quality["level"] == "warn"
    hr_flag = hr is not None and (hr > 100 or hr < 40)
    rm = byk.get("rmssd")
    very_low = bool(rm and rm["band"] and rm["value"] < 0.6 * rm["band"][0])
    eval_first = hr_flag or very_low                       # requiere evaluación profesional antes de seguir el plan
    ex_caution = eval_first or (age is not None and age >= 65) or bool(comorb)   # modera la intensidad del ejercicio
    stress_t = (m["stress_type"] or "")

    if poor:
        focus = ("Obtener una medición confiable", "La calidad técnica de esta medición limita la interpretación. Antes de sacar conclusiones conviene repetirla en condiciones estandarizadas.")
    elif hr_flag:
        focus = ("Contextualizar la frecuencia cardíaca con un profesional", f"La frecuencia cardíaca registrada ({es(hr, 0)} bpm) está fuera del rango habitual en reposo. Puede deberse a condiciones de la medición; se sugiere confirmarla y consultarla.")
    elif st("rmssd") == "low":
        focus = ("Favorecer la recuperación autonómica", "El RMSSD está por debajo de la referencia del protocolo para su perfil. El foco sugerido es el descanso, la regulación del estrés y un aumento gradual de la actividad.")
    elif st("lf_hf") == "high" or st("hr_mean") == "high":
        focus = ("Regulación del estrés y de la activación", "Algunos indicadores sugieren mayor activación en esta medición. El foco sugerido es la regulación del estrés y la repetición de la medición en reposo.")
    else:
        focus = ("Mantener hábitos y establecer una línea base", "Los indicadores con referencia disponibles no muestran alertas. El foco sugerido es sostener los hábitos y registrar mediciones comparables en el tiempo.")
    if not poor and stress_t.startswith("emocional"):
        focus = (focus[0], focus[1] + " El protocolo HBA identificó predominio de carga emocional.")
    elif not poor and stress_t.startswith("fisico"):
        focus = (focus[0], focus[1] + " El protocolo HBA identificó predominio de carga física.")

    if ex_caution:
        act = ["Caminatas suaves y movilidad, sin esfuerzos intensos hasta consultar con un profesional.", "Si aparecen mareos, dolor en el pecho o palpitaciones, suspender y consultar."]
    elif st("rmssd") == "low":
        act = ["Actividad aeróbica de intensidad baja a moderada (caminata, bicicleta suave) de 20–30 min, 3 o 4 días.", "Evitar sesiones muy intensas en los días de baja recuperación."]
    else:
        act = ["Mantener actividad regular (la OMS sugiere 150–300 min semanales de intensidad moderada en adultos).", "Alternar días de mayor y menor exigencia."]

    weeks = [
        ("moon", "Sueño", ["Horario regular de acostarse y levantarse, también el fin de semana.", "Dormitorio oscuro y fresco; evitar pantallas y comidas pesadas antes de dormir."]),
        ("heart", "Recuperación", ["Reservar pausas breves durante el día y al menos un día de descanso activo.", "Limitar alcohol, que suele reducir la variabilidad del ritmo cardíaco."]),
        ("run", "Actividad física", act),
        ("brain", "Manejo del estrés", ["Respiración lenta (cerca de 6 ciclos por minuto) 5–10 min por día.", "Identificar y anotar los momentos de mayor tensión del día."]),
        ("check", "Hábitos diarios", ["Comidas a horarios regulares; limitar cafeína desde la tarde.", "Exposición a luz natural por la mañana."]),
        ("drop", "Hidratación", ["Tomar líquidos de forma regular a lo largo del día.", "Las necesidades varían con el clima, la actividad y el estado de salud."]),
    ]
    priority = {"moon", "heart", "brain"} if st("rmssd") == "low" else ({"brain", "run"} if stress_t.startswith("emocional") else ({"heart"} if stress_t.startswith("fisico") else {"moon"}))
    if poor:
        priority = set()
    week_cards = [{"icon": i, "title": t, "items": it, "priority": i in priority} for i, t, it in weeks]
    week_cards.sort(key=lambda c: not c["priority"])
    checklist = ["Dormir a horario regular", "Respiración lenta 5–10 min", "Movimiento diario", "Líquidos regulares", "Sin cafeína tarde / pantallas"]

    d0 = now_local
    def dstr(n):
        d = d0 + timedelta(days=n)
        return f"{d.day} {MONTHS[d.month - 1]}"
    month = [
        ("Semana 1", "Línea base y rutina", "Fijar horario de sueño y momento diario de respiración. Medir una vez, en condiciones estandarizadas."),
        ("Semana 2", "Consistencia", "Sostener las rutinas. Repetir la medición con el mismo método, hora y duración."),
        ("Semana 3", "Progresión prudente", "Aumentar gradualmente la actividad solo si no hay alertas ni indicación profesional en contra."),
        ("Semana 4", "Reevaluación", "Medir y comparar con la línea base. Definir qué hábitos continuar."),
    ]
    if poor:
        month[0] = ("Semana 1", "Medición confiable", "Repetir la medición en 24–48 h siguiendo las indicaciones de preparación y usar esa medición como línea base.")
    control = ["RMSSD (indicador principal)", "Frecuencia cardíaca en reposo", "SDNN"]
    if (dur or 0) >= 5:
        control.append("LF/HF (con registros de 5 min)")
    control.append("Calidad de la señal y % de artefactos")
    if st("rmssd") == "low":
        control.append("Calidad del sueño y nivel de estrés percibido (autorregistro)")

    if poor:
        nxt = ("En 24–48 horas", "Repetir la medición con el mismo método, en reposo y sin cafeína previa, para disponer de una línea base confiable.", dstr(2))
    elif eval_first:
        nxt = ("Después de la evaluación profesional", "Retomar el seguimiento una vez evaluado el contexto clínico; luego medir cada 1–2 semanas.", None)
    else:
        nxt = ("En 7 días", "Luego cada 1–2 semanas durante el primer mes, con el mismo horario, postura, método y duración." + (" Con historial previo, cada 2 semanas puede ser suficiente." if n_hist >= 2 else ""), dstr(7))
    safety = []
    if eval_first:
        safety.append("Por los valores de esta medición, se sugiere consultar con un profesional de la salud antes de aumentar la intensidad del ejercicio.")
    elif ex_caution:
        safety.append("Dado el contexto registrado (edad o condiciones clínicas), conviene coordinar con su profesional tratante antes de aumentar la intensidad del ejercicio.")
    safety.append("Este plan es orientativo. No incluye tratamientos ni cambios de medicación.")
    return {"focus": focus, "weeks": week_cards, "checklist": checklist, "month": month, "control": control,
            "next": nxt, "safety": safety, "dates": [dstr(7), dstr(14), dstr(30)], "prof_first": ex_caution, "eval_first": eval_first}


# ── evolución ────────────────────────────────────────────────────────────────────────────────────────────
SERIES = [("rmssd", "RMSSD", "ms", 1), ("sdnn", "SDNN", "ms", 1), ("hr_mean", "Frecuencia cardíaca", "bpm", 0),
          ("pnn50", "pNN50", "%", 1), ("lf_hf", "LF/HF", "", 2), ("lnrmssd", "lnRMSSD", "", 2), ("carga_autonomica", "Carga autonómica", "", 0)]


def point_from_row(row, ts):
    n = normalize_metrics(row)
    d = {"ts": ts, "sensor": n["sensor_type"], "dur": n["duration_minutes"], "rmssd": n["rmssd_main"]}
    for k, _, _, _ in SERIES[1:]:
        d[k] = (n["cargas"].get("carga_autonomica") or {}).get("value") if k == "carga_autonomica" else n.get(k)
    return d


def build_evolution(cur_pt, history, cur_ts, tz, age, sex):
    pts = []
    for row in history or []:
        ts = parse_ts(row.get("timestamp_utc")) if isinstance(row, dict) else None
        if ts is None or ts > cur_ts + timedelta(seconds=1):
            continue
        p = point_from_row(row, ts)
        dup = (p["rmssd"] is not None and cur_pt["rmssd"] is not None and abs(p["rmssd"] - cur_pt["rmssd"]) < 0.05
               and p["hr_mean"] is not None and cur_pt["hr_mean"] is not None and abs(p["hr_mean"] - cur_pt["hr_mean"]) < 0.5)
        if dup:
            continue
        pts.append(p)
    pts.append(cur_pt)
    pts.sort(key=lambda p: p["ts"])
    pts = pts[-30:]
    series = []
    for key, name, unit, dec in SERIES:
        xs = [(p["ts"], p[key]) for p in pts if p.get(key) is not None]
        if len(xs) < 2:
            continue
        first, last = xs[0][1], xs[-1][1]
        delta = last - first
        pct = (delta / first * 100) if first else None
        series.append({"key": key, "name": name, "unit": unit, "dec": dec, "points": xs, "first": first, "last": last,
                       "delta": delta, "pct": pct, "t0": xs[0][0], "t1": xs[-1][0]})
    sensors = sorted({p["sensor"] for p in pts if p["sensor"]})
    durs = sorted({p["dur"] for p in pts if p["dur"]})
    band = band_for("rmssd", age, sex)
    return {"n": len(pts), "series": series, "mixed_methods": len(sensors) > 1,
            "methods": [R.SENSOR_LABEL[s] for s in sensors], "mixed_dur": len(durs) > 1, "rmssd_band": band,
            "baseline": len(pts) < 2 or not series}


def evolution_notes(ev, tz):
    out = []
    for s in ev["series"][:4]:
        pct = f" ({'+' if s['pct'] and s['pct'] > 0 else ''}{es(s['pct'], 0)} %)" if s["pct"] is not None else ""
        sign = "+" if s["delta"] > 0 else ("−" if s["delta"] < 0 else "")
        out.append(f"{s['name']}: de {es(s['first'], s['dec'])} a {es(s['last'], s['dec'])}{(' ' + s['unit']) if s['unit'] else ''} entre {fmt_d(s['t0'], tz)} y {fmt_d(s['t1'], tz)} (cambio {sign}{es(abs(s['delta']), s['dec'])}){pct}.")
    cautions = (["La medición actual no se incluye en las tendencias porque su señal no es válida."] if ev.get("excluded") else []) + ["Los cambios se describen sin atribuir una causa: varios factores (sueño, estrés, cafeína, hora, postura) pueden influir.",
                "Las variaciones entre días son normales y no siempre tienen significado clínico; interesa la tendencia sostenida."]
    if ev["mixed_methods"]:
        cautions.append("Las mediciones usaron métodos distintos (" + ", ".join(ev["methods"]) + "): comparar con cautela.")
    if ev["mixed_dur"]:
        cautions.append("Las mediciones tuvieron duraciones distintas, lo que afecta a SDNN y a los indicadores espectrales.")
    return out, cautions


# ── API principal ───────────────────────────────────────────────────────────────────────────────────────────
def clean_rr(rr):
    out = []
    for v in (rr or [])[:6000]:
        f = num(v)
        if f is not None and 200 <= f <= 2500:
            out.append(f)
    return out if len(out) >= 12 else []


def build_model(payload, now=None):
    payload = payload or {}
    tz = int(max(-840, min(840, num(payload.get("tz_offset_min")) or 0)))
    now = now or datetime.now(timezone.utc)
    age = num(payload.get("age"))
    age = age if age is not None and 0 <= age <= 120 else None
    sex = str(payload.get("sex") or "").upper().strip()
    sex = sex if sex in ("M", "F") else None
    pid = clip(payload.get("patient_id"), 48) or "Sin identificar"
    comorb, notes = clip(payload.get("comorbidities"), 160), clip(payload.get("notes"), 200)

    raw = payload.get("metrics") or {}
    m = normalize_metrics(raw)
    cur_ts = parse_ts(payload.get("measured_at")) or parse_ts(raw.get("timestamp_utc")) or now
    dur = m["duration_minutes"]
    sensor = m["sensor_type"]
    method = R.SENSOR_LABEL.get(sensor, "Método no registrado")
    conf, conf_txt = sensor_conf(sensor)
    alerts = technical_alerts(m)
    quality = signal_quality(m, alerts)
    ind = build_indicators(m, age, sex, conf, quality["level"], dur, alerts["severity"] == "invalid")
    if not ind:
        raise ValueError("La medición no contiene indicadores HRV calculados.")

    when = fmt_dt(cur_ts, tz)
    hist = payload.get("history") or []
    cur_pt = point_from_row(raw, cur_ts)
    if alerts["severity"] == "invalid":
        cur_pt = {k: (v if k in ("ts", "sensor", "dur") else None) for k, v in cur_pt.items()}
    ev = build_evolution(cur_pt, hist, cur_ts, tz, age, sex)
    n_prev = max(0, ev["n"] - 1)
    ev["excluded"] = alerts["severity"] == "invalid"
    ev["n"] = ev["n"] - (1 if ev["excluded"] else 0)
    ev["notes"], ev["cautions"] = evolution_notes(ev, tz)
    now_local = local(now, tz)

    plan = build_plan(ind, alerts, quality, m, dur, conf, age, comorb, n_prev, now_local)
    rr = clean_rr(payload.get("rr_ms"))
    seed = f"{pid}|{cur_ts.isoformat()}|{m['rmssd_main']}|{m['hr_mean']}"
    model = {
        "patient": {"id": pid, "age": age, "sex": sex, "comorbidities": comorb, "notes": notes},
        "when": when, "when_dt": cur_ts, "tz": tz, "generated": fmt_dt(now, tz), "now_local": now_local,
        "report_id": "HBA-" + hashlib.sha1(seed.encode()).hexdigest()[:8].upper(),
        "method": method, "sensor": sensor, "confidence": conf, "confidence_text": conf_txt,
        "duration": dur, "quality": quality, "alerts": alerts, "metrics": m, "indicators": ind,
        "rr": rr, "rr_count": len(rr),
        "findings": findings(ind, alerts, quality, m, dur, age),
        "summary": summary_text(ind, alerts, m, dur, method, when, age, sex),
        "interp": interpretation_rows(ind), "together": together_notes(ind, dur),
        "limits": limitations(ind, m, dur, conf, conf_txt, age, n_prev, alerts),
        "plan": plan, "evolution": ev,
        "cargas": [(k, label, m["cargas"][k]) for k, label in R.CARGAS if k in m["cargas"]],
        "hba_label": m["semaphore_label"], "stress_type": m["stress_type"],
        "sources": R.SOURCES, "disclaimer": R.DISCLAIMER,
    }
    return model

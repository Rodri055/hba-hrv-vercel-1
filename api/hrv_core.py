"""
HBA v2.0 — hrv_core.py
Lógica HRV compartida entre todas las funciones serverless de Vercel.
No importar Flask aquí — este módulo es puro cómputo científico.
"""

import os
import numpy as np
from scipy import interpolate, signal

# ── NeuroKit2 con import lazy para reducir cold-start ──────────────
def _nk():
    import neurokit2 as nk
    return nk


# ─────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────

def _as_float(x):
    try:
        if x is None or x == "":
            return np.nan
        return float(x)
    except Exception:
        return np.nan


def _finite_array(x):
    x = np.asarray(x, dtype=float)
    return x[np.isfinite(x)]


def sanitize_for_json(obj):
    if obj is None:
        return None
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if np.isfinite(v) else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    return obj


# ─────────────────────────────────────────
# Limpieza de RR
# ─────────────────────────────────────────

def clean_rri_ms(rri_ms: np.ndarray):
    rri_ms = _finite_array(rri_ms)
    if len(rri_ms) < 10:
        return rri_ms, np.nan, np.zeros(len(rri_ms), dtype=bool)

    bad = (rri_ms < 300) | (rri_ms > 2000)
    base = rri_ms[~bad] if np.any(~bad) else rri_ms
    med = np.median(base)
    mad = np.median(np.abs(base - med)) + 1e-9
    robust_z = 0.6745 * (rri_ms - med) / mad
    bad = bad | (np.abs(robust_z) > 4.5)

    artifact_percent = 100.0 * (np.sum(bad) / len(rri_ms))
    if not np.any(bad):
        return rri_ms, artifact_percent, bad

    idx = np.arange(len(rri_ms))
    good_idx = idx[~bad]
    if len(good_idx) < 3:
        return rri_ms, artifact_percent, bad

    f = interpolate.interp1d(good_idx, rri_ms[~bad], kind="linear",
                             fill_value="extrapolate", bounds_error=False)
    rri_clean = rri_ms.copy()
    rri_clean[bad] = f(idx[bad])
    return rri_clean, artifact_percent, bad


def _kubios_mask(rr_ms: np.ndarray, win=11):
    rr = _finite_array(rr_ms)
    n = rr.size
    if n < 15:
        return np.zeros(n, dtype=bool)
    w = max(7, min(int(win) | 1, 21))
    half = w // 2
    med_local = np.array([np.median(rr[max(0, i-half):min(n, i+half+1)]) for i in range(n)])
    rel_dev = np.abs(rr - med_local) / (med_local + 1e-9)
    drr = np.abs(np.diff(rr, prepend=rr[0])) / (med_local + 1e-9)
    return (rel_dev > 0.20) | (drr > 0.25) | (rr < 300) | (rr > 2000)


def _interp_bad(rr_ms, bad_mask):
    rr = np.asarray(rr_ms, dtype=float)
    bad = np.asarray(bad_mask, dtype=bool)
    n = rr.size
    if n < 3 or not np.any(bad):
        return rr
    idx = np.arange(n)
    good_idx = idx[~bad]
    if good_idx.size < 3:
        return rr
    f = interpolate.interp1d(good_idx, rr[~bad], kind="linear",
                             fill_value="extrapolate", bounds_error=False)
    out = rr.copy()
    out[bad] = f(idx[bad])
    return out


def windowed_rr_salvage(rr_ms, window_beats=40, step_beats=20, max_artifact_pct=25.0):
    rr = _finite_array(rr_ms)
    n = rr.size
    if n < 20:
        return rr, 0.0, np.nan

    w, s = max(25, int(window_beats)), max(10, int(step_beats))
    segments, qualities = [], []

    for start in range(0, n - w + 1, s):
        seg = rr[start:start + w]
        bad = _kubios_mask(seg)
        art = 100.0 * bad.mean()
        if art <= max_artifact_pct:
            segments.append(_interp_bad(seg, bad))
            qualities.append(100.0 - art)

    if not segments:
        bad_all = _kubios_mask(rr)
        art = 100.0 * bad_all.mean()
        return _interp_bad(rr, bad_all), max(0.0, 1 - art / 100), art

    order = np.argsort(qualities)[::-1]
    rr_rescued = np.concatenate([segments[i] for i in order])[:n]
    bad_all = _kubios_mask(rr)
    art_global = 100.0 * bad_all.mean()
    return rr_rescued, min(1.0, max(0.0, len(rr_rescued) / max(1, n))), art_global


# ─────────────────────────────────────────
# Métricas no lineales
# ─────────────────────────────────────────

def compute_poincare(rr_ms):
    rr = _finite_array(rr_ms)
    if rr.size < 10:
        return np.nan, np.nan, np.nan
    d = np.diff(rr)
    sd1 = float(np.sqrt(0.5 * np.var(d, ddof=1))) if len(d) > 1 else np.nan
    sd2 = float(np.sqrt(max(0, 2 * np.var(rr, ddof=1) - 0.5 * np.var(d, ddof=1)))) if len(d) > 1 else np.nan
    ratio = (sd1 / sd2) if (np.isfinite(sd1) and np.isfinite(sd2) and sd2 > 0) else np.nan
    return sd1, sd2, ratio


def compute_dfa_alpha1(rr_ms):
    rr = _finite_array(rr_ms)
    n = rr.size
    if n < 32:
        return np.nan
    y = np.cumsum(rr - np.mean(rr))
    scales = [s for s in [4, 6, 8, 10, 12, 16] if n >= s * 2]
    fn = []
    for s in scales:
        segs = n // s
        f2 = [np.mean((y[k*s:(k+1)*s] - np.polyval(np.polyfit(np.arange(s), y[k*s:(k+1)*s], 1), np.arange(s)))**2)
              for k in range(segs)]
        if f2:
            fn.append(np.sqrt(np.mean(f2)))
    if len(fn) < 3:
        return np.nan
    try:
        alpha, _ = np.polyfit(np.log(scales[:len(fn)]), np.log(np.array(fn) + 1e-12), 1)
        return float(alpha) if np.isfinite(alpha) else np.nan
    except Exception:
        return np.nan


# ─────────────────────────────────────────
# HRV core — desde RR
# ─────────────────────────────────────────

_DURATION_CORR = {1: 1.22, 3: 1.08, 5: 1.00}

def duration_correction(duration_minutes):
    try:
        dm = float(duration_minutes)
        if dm <= 1.5: return _DURATION_CORR[1]
        if dm <= 4.0: return _DURATION_CORR[3]
        return _DURATION_CORR[5]
    except Exception:
        return 1.0


def _hr_from_rr(rr):
    rr = _finite_array(rr)
    if rr.size < 3:
        return np.nan, np.nan, np.nan
    hr = 60000.0 / rr
    return float(np.nanmean(hr)), float(np.nanmax(hr)), float(np.nanmin(hr))


def rri_to_peaks(rri_ms, sampling_rate=1000):
    rri_ms = _finite_array(rri_ms)
    if len(rri_ms) < 3:
        return None
    peak_times = np.cumsum(rri_ms) / 1000.0
    peak_samples = np.unique(np.round(peak_times * sampling_rate).astype(int))
    if len(peak_samples) < 3:
        return None
    length = int(peak_samples[-1] + sampling_rate)
    peaks = np.zeros(length, dtype=int)
    peaks[peak_samples] = 1
    return peaks


def compute_hrv_from_rri(rri_ms, duration_minutes=None):
    nk = _nk()
    rri_ms = _finite_array(rri_ms)
    if len(rri_ms) < 12:
        return {"error": "Insuficientes intervalos RR (mínimo 12)."}

    rr_rescued, usable_ratio, art_global = windowed_rr_salvage(rri_ms)
    rr_clean, art_mad, _ = clean_rri_ms(rr_rescued)

    artifact_percent = float(
        0.65 * art_global + 0.35 * art_mad
        if np.isfinite(art_global) and np.isfinite(art_mad)
        else art_global if np.isfinite(art_global) else art_mad
    )

    hr_mean, hr_max, hr_min = _hr_from_rr(rr_clean)
    sd1, sd2, sd_ratio = compute_poincare(rr_clean)
    dfa1 = compute_dfa_alpha1(rr_clean)

    try:
        hrv_time = nk.hrv_time(rri=rr_clean, show=False)
        hrv_freq = nk.hrv_frequency(rri=rr_clean, show=False)
    except Exception:
        peaks = rri_to_peaks(rr_clean)
        if peaks is None:
            return {"error": "No se pudo construir tren de picos."}
        hrv_time = nk.hrv_time(peaks, sampling_rate=1000, show=False)
        hrv_freq = nk.hrv_frequency(peaks, sampling_rate=1000, show=False)

    def g(df, key):
        try:
            return _as_float(df[key].iloc[0])
        except Exception:
            return np.nan

    rmssd = g(hrv_time, "HRV_RMSSD")
    sdnn  = g(hrv_time, "HRV_SDNN")
    pnn50 = g(hrv_time, "HRV_pNN50")
    mean_rr = g(hrv_time, "HRV_MeanNN")
    lf  = g(hrv_freq, "HRV_LF")
    hf  = g(hrv_freq, "HRV_HF")
    tp  = g(hrv_freq, "HRV_TP")
    lfhf = (lf / hf) if (np.isfinite(lf) and np.isfinite(hf) and hf > 0) else np.nan

    corr = duration_correction(duration_minutes)
    rmssd_corr = rmssd * corr if np.isfinite(rmssd) else np.nan
    lnrmssd = np.log(rmssd_corr) if np.isfinite(rmssd_corr) and rmssd_corr > 0 else np.nan

    freq_warning = None
    try:
        if duration_minutes and float(duration_minutes) < 5:
            freq_warning = "Test < 5 min: LF/HF es orientativo."
    except Exception:
        pass

    return {
        "rmssd": rmssd, "rmssd_corr": rmssd_corr, "sdnn": sdnn,
        "lnrmssd": lnrmssd, "pnn50": pnn50, "mean_rr": mean_rr,
        "lf_power": lf, "hf_power": hf, "lf_hf": lfhf, "total_power": tp,
        "sd1": sd1, "sd2": sd2, "sd1_sd2_ratio": sd_ratio, "dfa_alpha1": dfa1,
        "artifact_percent": artifact_percent,
        "usable_ratio": float(usable_ratio) if np.isfinite(usable_ratio) else None,
        "quality_score": float(np.clip(100 - artifact_percent, 0, 100)) if np.isfinite(artifact_percent) else None,
        "n_rr": int(len(rr_clean)),
        "hr_mean": hr_mean, "hr_max": hr_max, "hr_min": hr_min,
        "freq_warning": freq_warning,
        "duration_correction": corr,
    }


def compute_hrv_from_ppg(ppg, sampling_rate, duration_minutes=None):
    nk = _nk()
    ppg = _finite_array(ppg)
    if not (np.isfinite(sampling_rate) and sampling_rate > 1):
        return {"error": "sampling_rate inválido."}
    if len(ppg) < int(sampling_rate * 45):
        return {"error": "PPG insuficiente (mínimo 45 seg)."}

    ppg = (ppg - np.nanmean(ppg)) / (np.nanstd(ppg) + 1e-9)
    try:
        ppg_f = nk.signal_filter(ppg, sampling_rate=sampling_rate,
                                  lowcut=0.7, highcut=5.0, method="butterworth", order=3)
    except Exception:
        ppg_f = ppg

    # Detección de picos
    peaks_idx = None
    try:
        _, info = nk.ppg_peaks(ppg_f, sampling_rate=sampling_rate, method="elgendi")
        p = info.get("PPG_Peaks", info.get("peaks"))
        if p is not None:
            p = np.asarray(p, dtype=int)
            p = p[(p > 0) & (p < len(ppg_f))]
            if len(p) >= 12:
                peaks_idx = p
    except Exception:
        pass

    if peaks_idx is None:
        min_dist = max(1, int(0.33 * sampling_rate))
        amp = np.percentile(ppg_f, 95) - np.percentile(ppg_f, 5)
        peaks_idx, _ = signal.find_peaks(ppg_f, distance=min_dist, prominence=max(0.10, 0.15 * amp))
        peaks_idx = np.asarray(peaks_idx, dtype=int)
        peaks_idx = peaks_idx[(peaks_idx > 0) & (peaks_idx < len(ppg_f))]
        if len(peaks_idx) < 12:
            return {"error": "No se detectaron picos PPG confiables."}

    rr_ms = np.diff(peaks_idx) / sampling_rate * 1000.0
    rr_ms = rr_ms[np.isfinite(rr_ms)]
    if len(rr_ms) < 12:
        return {"error": "PPG: RR insuficientes tras detección de picos."}

    result = compute_hrv_from_rri(rr_ms, duration_minutes=duration_minutes)
    result["n_peaks"] = int(len(peaks_idx))
    result["sampling_rate"] = float(sampling_rate)

    # Frecuencia respiratoria por FFT
    try:
        rsp = nk.signal_filter(ppg_f, sampling_rate=sampling_rate,
                               lowcut=0.1, highcut=0.4, method="butterworth", order=3)
        freqs = np.fft.rfftfreq(len(rsp), d=1.0 / sampling_rate)
        spec  = np.abs(np.fft.rfft(rsp)) ** 2
        mask  = (freqs >= 0.1) & (freqs <= 0.4)
        if np.any(mask):
            f0 = freqs[mask][int(np.argmax(spec[mask]))]
            result["resp_rate_rpm"] = float(f0 * 60.0)
    except Exception:
        result["resp_rate_rpm"] = None

    return result


# ─────────────────────────────────────────
# HBA Dashboard
# ─────────────────────────────────────────

def baevsky_index(nn_ms):
    nn_ms = _finite_array(nn_ms)
    if nn_ms.size < 30:
        return np.nan
    hist, edges = np.histogram(nn_ms, bins=50)
    idx = int(np.argmax(hist))
    Mo  = float((edges[idx] + edges[idx + 1]) / 2.0)
    AMo = float(hist[idx] / nn_ms.size * 100.0)
    MxDMn = float(np.max(nn_ms) - np.min(nn_ms))
    if Mo <= 0 or MxDMn <= 0:
        return np.nan
    SI = AMo / (2.0 * (Mo / 1000.0) * (MxDMn / 1000.0))
    return float(SI) if np.isfinite(SI) else np.nan


def classify_hml(value, low, high):
    v = _as_float(value)
    if not np.isfinite(v):
        return "insuficiente"
    if v < low:  return "bajo"
    if v > high: return "alto"
    return "medio"


def rmssd_reference(age, sex):
    a = _as_float(age)
    s = str(sex).upper().strip() if sex else "X"
    if not np.isfinite(a):
        return 25.0, 55.0
    a = int(a)
    if a < 20:   lo, hi = 35.0, 80.0
    elif a < 30: lo, hi = 30.0, 70.0
    elif a < 40: lo, hi = 25.0, 60.0
    elif a < 50: lo, hi = 20.0, 50.0
    elif a < 60: lo, hi = 18.0, 45.0
    else:        lo, hi = 15.0, 40.0
    if s == "F": hi += 2.0
    return float(lo), float(hi)


# ── Semáforo clínico ──────────────────────────────────────────────

SEMAPHORE_LEVELS = {
    "optimo": {
        "label": "Óptimo",
        "color": "#16a34a", "color_light": "#dcfce7", "icon": "▲",
        "description": "Sistema nervioso autónomo altamente flexible. Excelente capacidad de adaptación y recuperación.",
        "plan": [
            {"item": "Carga fascial y miofascial a máxima intensidad", "pct": 100},
            {"item": "Ejercicios biomecánicos funcionales de alta demanda", "pct": 60},
            {"item": "Ejercicios de columna con carga completa", "pct": 40},
            {"item": "Equilibrio SNA (mantenimiento)", "pct": 20},
            {"item": "Relax activo post-sesión", "pct": 10},
        ]
    },
    "funcional": {
        "label": "Funcional",
        "color": "#2563eb", "color_light": "#dbeafe", "icon": "●",
        "description": "HRV dentro de rango normal. Leve activación simpática, sistema bien compensado.",
        "plan": [
            {"item": "Tejido miofascial (60–70% tensión e intensidad)", "pct": 70},
            {"item": "Equilibrio SNA (respiración, coherencia)", "pct": 40},
            {"item": "Ejercicios biomecánicos funcionales", "pct": 40},
            {"item": "Ejercicios de columna", "pct": 30},
            {"item": "Relax post-sesión", "pct": 10},
        ]
    },
    "comprometido": {
        "label": "Comprometido",
        "color": "#d97706", "color_light": "#fef3c7", "icon": "▼",
        "description": "HRV reducida. Carga autonómica elevada. Priorizar recuperación y técnicas vagales.",
        "plan": [
            {"item": "Equilibrio SNA / patrón respiratorio / coherencia cardíaca", "pct": 60},
            {"item": "Tejido miofascial (40% tensión, técnicas suaves)", "pct": 40},
            {"item": "Ejercicios de columna (carga baja)", "pct": 20},
            {"item": "Ejercicio biomecánico funcional adaptado", "pct": 20},
            {"item": "Relax profundo", "pct": 20},
        ]
    },
    "critico": {
        "label": "Crítico",
        "color": "#dc2626", "color_light": "#fee2e2", "icon": "⚠",
        "description": "HRV muy baja. Intervención prioritaria. Derivar si persiste o hay síntomas asociados.",
        "plan": [
            {"item": "Equilibrio SNA intensivo (visualización, respiración 4-7-8)", "pct": 80},
            {"item": "Tejido miofascial muy suave (sin carga)", "pct": 20},
            {"item": "Movilidad articular pasiva", "pct": 15},
            {"item": "Relax profundo / relajación progresiva", "pct": 30},
            {"item": "Evaluación médica si persiste más de 48 h", "pct": 0},
        ]
    },
}


def classify_semaphore(rmssd_corr, rmssd_low, rmssd_high, auto_score):
    rmssd = _as_float(rmssd_corr)
    score = _as_float(auto_score)
    if not np.isfinite(rmssd):
        return "funcional"
    if rmssd >= rmssd_high * 1.15 or (np.isfinite(score) and score < 20):
        return "optimo"
    if rmssd < rmssd_low * 0.65  or (np.isfinite(score) and score > 75):
        return "critico"
    if rmssd >= rmssd_low:
        return "funcional"
    return "comprometido"


def compute_cargas(rmssd, sdnn, pnn50, lf_hf, hr_mean, baevsky, sd1, dfa_alpha1):

    def _w(val, lo, hi, invert, w):
        v = _as_float(val)
        if not np.isfinite(v):
            return None, 0
        norm = np.clip((v - lo) / (hi - lo + 1e-9), 0, 1)
        return float(norm if not invert else 1 - norm) * w, w

    def _score(parts):
        vals = [v for v, _ in parts if v is not None]
        ws   = [w for v, w in parts if v is not None]
        if not vals:
            return np.nan
        return float(np.sum(vals) / max(np.sum(ws), 1e-9) * 100)

    ca = _score([
        _w(rmssd,   15,  80,  True,  0.40),
        _w(lf_hf,   1.0, 5.0, False, 0.35),
        _w(baevsky, 50,  500, False, 0.25),
    ])

    ce = _score([
        _w(rmssd, 15, 70, True, 0.45),
        _w(pnn50,  2, 40, True, 0.30),
        _w(sd1,    8, 50, True, 0.25),
    ])

    cf = _score([
        _w(sdnn,       20,  80,  True, 0.40),
        _w(hr_mean,    55,  95,  False,0.35),
        _w(dfa_alpha1, 0.5, 1.5, True, 0.25),
    ])

    es = _score([
        _w(baevsky, 50,  500, False, 0.50),
        _w(lf_hf,   1.0, 5.0, False, 0.30),
        _w(hr_mean, 55,  95,  False, 0.20),
    ])

    def _level(s):
        if not np.isfinite(s): return "insuficiente"
        if s < 30: return "bajo"
        if s < 60: return "moderado"
        if s < 80: return "alto"
        return "muy alto"

    return {
        "carga_autonomica": {"value": ca, "level": _level(ca)},
        "carga_emocional":  {"value": ce, "level": _level(ce)},
        "carga_fisica":     {"value": cf, "level": _level(cf)},
        "estres":           {"value": es, "level": _level(es)},
    }


def enrich_dashboard(result: dict, payload: dict):
    if result.get("error"):
        return result

    age = payload.get("age")
    sex = payload.get("sex")

    rmssd      = _as_float(result.get("rmssd"))
    rmssd_corr = _as_float(result.get("rmssd_corr", result.get("rmssd")))
    sdnn       = _as_float(result.get("sdnn"))
    lnrmssd    = _as_float(result.get("lnrmssd"))
    pnn50      = _as_float(result.get("pnn50"))
    lfhf       = _as_float(result.get("lf_hf"))
    hr_mean    = _as_float(result.get("hr_mean"))
    sd1        = _as_float(result.get("sd1"))
    sd2        = _as_float(result.get("sd2"))
    dfa1       = _as_float(result.get("dfa_alpha1"))

    # Baevsky — desde RR si disponible
    baevsky = np.nan
    rri_raw = payload.get("rri_ms", [])
    if rri_raw and len(rri_raw) >= 30:
        rr = _finite_array(np.array(rri_raw, dtype=float))
        rr_clean, _, _ = clean_rri_ms(rr)
        baevsky = baevsky_index(rr_clean)

    rm_low, rm_high = rmssd_reference(age, sex)
    rm_state = classify_hml(rmssd_corr, rm_low, rm_high)
    cargas   = compute_cargas(rmssd_corr, sdnn, pnn50, lfhf, hr_mean, baevsky, sd1, dfa1)
    ca_score = cargas["carga_autonomica"]["value"]
    sem_key  = classify_semaphore(rmssd_corr, rm_low, rm_high, ca_score)
    sem_data = SEMAPHORE_LEVELS[sem_key]

    biomarkers = [
        {"name": "RMSSD",           "value": rmssd,     "value_corr": rmssd_corr, "unit": "ms",  "state": rm_state,                          "detail": f"Ref: {rm_low:.0f}–{rm_high:.0f} ms (edad/sexo)"},
        {"name": "lnRMSSD",         "value": lnrmssd,   "unit": "",   "state": "informativo",                                                  "detail": "Logaritmo RMSSD corregido"},
        {"name": "SDNN",            "value": sdnn,      "unit": "ms", "state": classify_hml(sdnn, 30, 60),                                     "detail": "Variabilidad global"},
        {"name": "FC media",        "value": hr_mean,   "unit": "bpm","state": classify_hml(hr_mean, 60, 85),                                  "detail": ""},
        {"name": "LF/HF",           "value": lfhf,      "unit": "",   "state": classify_hml(lfhf, 1.5, 3.0),                                  "detail": result.get("freq_warning") or ""},
        {"name": "Baevsky (SI)",     "value": baevsky,   "unit": "",   "state": classify_hml(baevsky, 150, 300),                                "detail": "Alto SI = mayor tensión autonómica"},
        {"name": "SD1 (Poincaré)",  "value": sd1,       "unit": "ms", "state": classify_hml(sd1, 10, 50),                                      "detail": "Variabilidad corto plazo (vagal)"},
        {"name": "SD2 (Poincaré)",  "value": sd2,       "unit": "ms", "state": classify_hml(sd2, 20, 80),                                      "detail": "Variabilidad largo plazo"},
        {"name": "DFA α1",          "value": dfa1,      "unit": "",   "state": classify_hml(dfa1, 0.75, 1.5),                                  "detail": "< 0.75 indica desregulación"},
    ]

    result["hba_dashboard"] = {
        "biomarkers": biomarkers,
        "cargas": cargas,
        "norms": {"age": age, "sex": sex, "rmssd_low": rm_low, "rmssd_high": rm_high, "rmssd_state": rm_state},
        "semaphore": {
            "key": sem_key, "label": sem_data["label"],
            "color": sem_data["color"], "color_light": sem_data["color_light"],
            "icon": sem_data["icon"], "description": sem_data["description"],
            "plan": sem_data["plan"],
        },
    }
    return result

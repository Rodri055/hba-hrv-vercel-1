"""
HBA v2.0 — hrv_core.py
PROTOCOLO: RMSSD corregido por edad/sexo como métrica principal.
Todos los sensores terminan en NN (RR sin artefactos).
"""
import numpy as np
from scipy import interpolate, signal as scipy_signal

def _nk():
    import neurokit2 as nk
    return nk

def _f(x):
    try:
        if x is None or x == "": return np.nan
        return float(x)
    except: return np.nan

def _arr(x):
    x = np.asarray(x, dtype=float)
    return x[np.isfinite(x)]

def sanitize_for_json(obj):
    if obj is None: return None
    if isinstance(obj, (np.floating, float)):
        v = float(obj); return v if np.isfinite(v) else None
    if isinstance(obj, (np.integer, int)): return int(obj)
    if isinstance(obj, dict): return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)): return [sanitize_for_json(v) for v in obj]
    return obj

# ── Limpieza RR → NN ─────────────────────────────────────────

def _kubios_mask(rr):
    rr = _arr(rr); n = rr.size
    if n < 15: return np.zeros(n, dtype=bool)
    w = max(7, min(int(11) | 1, 21)); half = w // 2
    med_local = np.array([np.median(rr[max(0,i-half):min(n,i+half+1)]) for i in range(n)])
    rel_dev = np.abs(rr - med_local) / (med_local + 1e-9)
    drr = np.abs(np.diff(rr, prepend=rr[0])) / (med_local + 1e-9)
    return (rel_dev > 0.20) | (drr > 0.25) | (rr < 300) | (rr > 2000)

def _interp_bad(rr, bad):
    rr = np.asarray(rr, dtype=float); bad = np.asarray(bad, dtype=bool); n = rr.size
    if n < 3 or not np.any(bad): return rr
    idx = np.arange(n); good = idx[~bad]
    if good.size < 3: return rr
    f = interpolate.interp1d(good, rr[~bad], kind="linear", fill_value="extrapolate", bounds_error=False)
    out = rr.copy(); out[bad] = f(idx[bad]); return out

def rr_to_nn(rr_ms):
    rr = _arr(rr_ms)
    if rr.size < 10: return rr, 100.0, np.ones(rr.size, dtype=bool)
    bad_phys = (rr < 300) | (rr > 2000)
    base = rr[~bad_phys] if np.any(~bad_phys) else rr
    if base.size < 5: return rr, 100.0, np.ones(rr.size, dtype=bool)
    med = np.median(base); mad = np.median(np.abs(base - med)) + 1e-9
    bad_mad = np.abs(0.6745 * (rr - med) / mad) > 4.5
    bad = bad_phys | bad_mad | _kubios_mask(rr)
    art = float(100.0 * np.sum(bad) / rr.size)
    return _interp_bad(rr, bad), art, bad

def windowed_nn_salvage(rr_ms, window_beats=45, step_beats=20, max_artifact_pct=30.0):
    rr = _arr(rr_ms); n = rr.size
    if n < 20: return rr, 0.0, np.nan
    w = max(25, int(window_beats)); s = max(10, int(step_beats))
    segs, quals = [], []
    for start in range(0, n - w + 1, s):
        seg = rr[start:start+w]; bad = _kubios_mask(seg); art = 100.0 * bad.mean()
        if art <= max_artifact_pct: segs.append(_interp_bad(seg, bad)); quals.append(100.0 - art)
    if not segs:
        bad_all = _kubios_mask(rr); art = 100.0 * bad_all.mean()
        return _interp_bad(rr, bad_all), max(0.0, 1-art/100), art
    order = np.argsort(quals)[::-1]
    nn_r = np.concatenate([segs[i] for i in order])[:n]
    art_g = 100.0 * _kubios_mask(rr).mean()
    return nn_r, min(1.0, max(0.0, nn_r.size/max(1,n))), art_g

# ── Métricas no lineales ──────────────────────────────────────

def compute_poincare(nn_ms):
    nn = _arr(nn_ms)
    if nn.size < 10: return np.nan, np.nan, np.nan
    d = np.diff(nn)
    if len(d) < 2: return np.nan, np.nan, np.nan
    sd1 = float(np.sqrt(0.5 * np.var(d, ddof=1)))
    sd2 = float(np.sqrt(max(0, 2*np.var(nn, ddof=1) - 0.5*np.var(d, ddof=1))))
    return sd1, sd2, (sd1/sd2 if sd2 > 0 else np.nan)

def compute_dfa_alpha1(nn_ms):
    nn = _arr(nn_ms); n = nn.size
    if n < 32: return np.nan
    y = np.cumsum(nn - np.mean(nn))
    scales = [s for s in [4,6,8,10,12,16] if n >= s*2]
    fn = []
    for sc in scales:
        f2 = [np.mean((y[k*sc:(k+1)*sc] - np.polyval(np.polyfit(np.arange(sc), y[k*sc:(k+1)*sc], 1), np.arange(sc)))**2) for k in range(n//sc)]
        if f2: fn.append(np.sqrt(np.mean(f2)))
    if len(fn) < 3: return np.nan
    try:
        alpha, _ = np.polyfit(np.log(scales[:len(fn)]), np.log(np.array(fn)+1e-12), 1)
        return float(alpha) if np.isfinite(alpha) else np.nan
    except: return np.nan

def baevsky_index(nn_ms):
    nn = _arr(nn_ms)
    if nn.size < 30: return np.nan
    hist, edges = np.histogram(nn, bins=50)
    idx = int(np.argmax(hist))
    Mo = float((edges[idx]+edges[idx+1])/2.0)
    AMo = float(hist[idx]/nn.size*100.0)
    MxDMn = float(np.max(nn)-np.min(nn))
    if Mo <= 0 or MxDMn <= 0: return np.nan
    SI = AMo / (2.0*(Mo/1000.0)*(MxDMn/1000.0))
    return float(SI) if np.isfinite(SI) else np.nan

# ── Corrección por duración ───────────────────────────────────
_DUR_CORR = {1: 1.22, 3: 1.08, 5: 1.00}
def duration_correction(dm):
    try:
        dm = float(dm)
        if dm <= 1.5: return 1.22
        if dm <= 4.0: return 1.08
        return 1.00
    except: return 1.0

# ── Cálculo HRV desde NN ──────────────────────────────────────

def _hr_from_nn(nn):
    nn = _arr(nn)
    if nn.size < 3: return np.nan, np.nan, np.nan
    hr = 60000.0/nn
    return float(np.nanmean(hr)), float(np.nanmax(hr)), float(np.nanmin(hr))

def _nn_to_peaks(nn_ms, sr=1000):
    nn = _arr(nn_ms)
    if nn.size < 3: return None
    pt = np.cumsum(nn)/1000.0
    ps = np.unique(np.round(pt*sr).astype(int))
    if ps.size < 3: return None
    peaks = np.zeros(int(ps[-1]+sr), dtype=int)
    peaks[ps] = 1
    return peaks

def compute_hrv_from_nn(nn_ms, artifact_pct, duration_minutes=None, sensor_type=""):
    nk = _nk(); nn = _arr(nn_ms)
    if nn.size < 12: return {"error": "NN insuficientes (mínimo 12 latidos)."}
    hr_mean, hr_max, hr_min = _hr_from_nn(nn)
    sd1, sd2, sd_ratio = compute_poincare(nn)
    dfa1 = compute_dfa_alpha1(nn)
    si = baevsky_index(nn)
    try:
        ht = nk.hrv_time(rri=nn, show=False)
        hf = nk.hrv_frequency(rri=nn, show=False)
    except:
        peaks = _nn_to_peaks(nn)
        if peaks is None: return {"error": "No se pudo calcular HRV."}
        try:
            ht = nk.hrv_time(peaks, sampling_rate=1000, show=False)
            hf = nk.hrv_frequency(peaks, sampling_rate=1000, show=False)
        except Exception as e: return {"error": f"Error HRV: {str(e)}"}
    def g(df, key):
        try: return _f(df[key].iloc[0])
        except: return np.nan
    rmssd=g(ht,"HRV_RMSSD"); sdnn=g(ht,"HRV_SDNN"); pnn50=g(ht,"HRV_pNN50"); mean_rr=g(ht,"HRV_MeanNN")
    lf=g(hf,"HRV_LF"); hf_v=g(hf,"HRV_HF"); tp=g(hf,"HRV_TP")
    lfhf = (lf/hf_v) if (np.isfinite(lf) and np.isfinite(hf_v) and hf_v>0) else np.nan
    corr = duration_correction(duration_minutes)
    rmssd_corr = rmssd*corr if np.isfinite(rmssd) else np.nan
    lnrmssd = np.log(rmssd_corr) if (np.isfinite(rmssd_corr) and rmssd_corr>0) else np.nan
    freq_warning = None
    try:
        if duration_minutes and float(duration_minutes) < 5:
            freq_warning = f"Test {duration_minutes} min: LF/HF orientativo. Para análisis espectral completo usar 5 min."
    except: pass
    return {
        "rmssd":rmssd,"rmssd_corr":rmssd_corr,"sdnn":sdnn,"lnrmssd":lnrmssd,"pnn50":pnn50,"mean_rr":mean_rr,
        "lf_power":lf,"hf_power":hf_v,"lf_hf":lfhf,"total_power":tp,
        "sd1":sd1,"sd2":sd2,"sd1_sd2_ratio":sd_ratio,"dfa_alpha1":dfa1,"baevsky":si,
        "hr_mean":hr_mean,"hr_max":hr_max,"hr_min":hr_min,
        "artifact_percent":artifact_pct,
        "quality_score":float(np.clip(100-artifact_pct,0,100)) if np.isfinite(artifact_pct) else None,
        "n_nn":int(nn.size),"duration_correction":corr,
        "freq_warning":freq_warning,"sensor_type":sensor_type,"duration_minutes":duration_minutes,
    }

# ── Pipelines por sensor ──────────────────────────────────────

def compute_hrv_from_rri(rri_ms, duration_minutes=None, sensor_type="polar_h10"):
    rr = _arr(rri_ms)
    if rr.size < 12: return {"error": "RR insuficientes (mínimo 12)."}
    nn_r, usable, art_g = windowed_nn_salvage(rr, max_artifact_pct=20.0)
    nn, art_mad, _ = rr_to_nn(nn_r)
    art = float(0.6*art_g+0.4*art_mad) if (np.isfinite(art_g) and np.isfinite(art_mad)) else (art_g if np.isfinite(art_g) else art_mad)
    result = compute_hrv_from_nn(nn, art, duration_minutes, sensor_type)
    result["usable_ratio"] = float(usable) if np.isfinite(usable) else None
    return result

def compute_hrv_from_ppg(ppg, sampling_rate, duration_minutes=None, sensor_type="camera_ppg"):
    nk = _nk(); ppg = _arr(ppg); sr = float(sampling_rate)
    if not (np.isfinite(sr) and sr > 1): return {"error": "sampling_rate inválido."}
    if ppg.size < int(sr*45): return {"error": "Señal insuficiente (mínimo 45 seg)."}
    ppg = (ppg - np.nanmean(ppg)) / (np.nanstd(ppg) + 1e-9)
    try:
        lo,hi = (0.5,4.0) if sensor_type != "vibration_scg" else (0.8,3.5)
        ppg_f = nk.signal_filter(ppg, sampling_rate=sr, lowcut=lo, highcut=hi, method="butterworth", order=3)
    except: ppg_f = ppg
    peaks_idx = None
    try:
        _, info = nk.ppg_peaks(ppg_f, sampling_rate=sr, method="elgendi")
        p = info.get("PPG_Peaks", info.get("peaks"))
        if p is not None:
            p = np.asarray(p, dtype=int); p = p[(p>0)&(p<ppg_f.size)]
            if p.size >= 12: peaks_idx = p
    except: pass
    if peaks_idx is None:
        min_dist = max(1, int(0.4*sr)); amp = np.percentile(ppg_f,95)-np.percentile(ppg_f,5)
        peaks_idx, _ = scipy_signal.find_peaks(ppg_f, distance=min_dist, prominence=max(0.08,0.12*amp))
        peaks_idx = np.asarray(peaks_idx,dtype=int); peaks_idx = peaks_idx[(peaks_idx>0)&(peaks_idx<ppg_f.size)]
        if peaks_idx.size < 12: return {"error": "No se detectaron picos confiables."}
    rr_ms = np.diff(peaks_idx)/sr*1000.0; rr_ms = rr_ms[np.isfinite(rr_ms)]
    if rr_ms.size < 12: return {"error": "RR insuficientes tras detección de picos."}
    nn_r, usable, art_g = windowed_nn_salvage(rr_ms, max_artifact_pct=30.0)
    nn, art_mad, _ = rr_to_nn(nn_r)
    art = float(0.6*art_g+0.4*art_mad) if (np.isfinite(art_g) and np.isfinite(art_mad)) else (art_g if np.isfinite(art_g) else art_mad)
    result = compute_hrv_from_nn(nn, art, duration_minutes, sensor_type)
    result["n_peaks"] = int(peaks_idx.size); result["sampling_rate"] = sr
    result["usable_ratio"] = float(usable) if np.isfinite(usable) else None
    try:
        rsp = nk.signal_filter(ppg_f, sampling_rate=sr, lowcut=0.1, highcut=0.4, method="butterworth", order=3)
        freqs = np.fft.rfftfreq(rsp.size, d=1.0/sr); spec = np.abs(np.fft.rfft(rsp))**2
        mask = (freqs>=0.1)&(freqs<=0.4)
        if np.any(mask): result["resp_rate_rpm"] = float(freqs[mask][int(np.argmax(spec[mask]))]*60.0)
    except: result["resp_rate_rpm"] = None
    if sensor_type in ("face_rppg","vibration_scg"):
        result["freq_warning"] = ((result.get("freq_warning") or "")+" Nota: señal orientativa (sensor no-contacto).").strip()
    return result

# ── Referencias normativas ────────────────────────────────────

def rmssd_reference(age, sex):
    a = _f(age); s = str(sex).upper().strip() if sex else "X"
    if not np.isfinite(a): return 25.0, 55.0
    a = int(a)
    if a<20:   lo,hi=38.0,85.0
    elif a<30: lo,hi=32.0,72.0
    elif a<40: lo,hi=27.0,62.0
    elif a<50: lo,hi=22.0,52.0
    elif a<60: lo,hi=18.0,45.0
    elif a<70: lo,hi=15.0,38.0
    else:      lo,hi=12.0,32.0
    if s=="F": hi+=3.0; lo+=1.0
    return float(lo), float(hi)

# ── Semáforo ──────────────────────────────────────────────────

SEMAPHORE = {
    "optimo":       {"label":"Óptimo",       "color":"#00d4aa","color_light":"#f0fdf9","icon":"▲","description":"SNA altamente flexible y resiliente. Excelente capacidad adaptativa. Estado ideal para intervención de alta intensidad."},
    "funcional":    {"label":"Funcional",    "color":"#3b8bff","color_light":"#eff6ff","icon":"●","description":"HRV dentro del rango normal. Leve activación simpática, sistema bien compensado. Apto para trabajo moderado-intenso."},
    "comprometido": {"label":"Comprometido","color":"#ffaa00","color_light":"#fffbeb","icon":"▼","description":"HRV reducida. Carga autonómica elevada. Priorizar recuperación y técnicas vagales."},
    "critico":      {"label":"Crítico",      "color":"#ff4560","color_light":"#fff1f2","icon":"⚠","description":"HRV muy baja. Intervención prioritaria. Consulta médica si persiste > 48 h."},
}

def classify_semaphore(rmssd_corr, rmssd_low, rmssd_high, ca_score):
    r=_f(rmssd_corr); s=_f(ca_score)
    if not np.isfinite(r): return "funcional"
    if r>=rmssd_high*1.15 or (np.isfinite(s) and s<18): return "optimo"
    if r<rmssd_low*0.60   or (np.isfinite(s) and s>78): return "critico"
    if r>=rmssd_low: return "funcional"
    return "comprometido"

# ── Cargas diferenciadas ──────────────────────────────────────

def compute_cargas(rmssd, sdnn, pnn50, lf_hf, hr_mean, baevsky, sd1, dfa_alpha1):
    def _w(val,lo,hi,inv,wt):
        v=_f(val)
        if not np.isfinite(v): return None,0.0
        norm=float(np.clip((v-lo)/(hi-lo+1e-9),0,1))
        return (norm if not inv else 1-norm)*wt, wt
    def _score(parts):
        vals=[v for v,_ in parts if v is not None]; ws=[w for v,w in parts if v is not None]
        return float(np.sum(vals)/max(np.sum(ws),1e-9)*100) if vals else np.nan
    ca=_score([_w(rmssd,15,80,True,0.40),_w(lf_hf,1.0,5.5,False,0.35),_w(baevsky,50,500,False,0.25)])
    ce=_score([_w(rmssd,15,70,True,0.40),_w(pnn50,2,40,True,0.25),_w(sd1,8,50,True,0.20),_w(lf_hf,1.0,5.0,False,0.15)])
    cf=_score([_w(sdnn,20,80,True,0.35),_w(hr_mean,55,95,False,0.30),_w(dfa_alpha1,0.5,1.5,True,0.35)])
    es=_score([_w(baevsky,50,500,False,0.45),_w(lf_hf,1.0,5.5,False,0.35),_w(hr_mean,55,95,False,0.20)])
    def _lv(s):
        if not np.isfinite(s): return "insuficiente"
        if s<25: return "bajo"
        if s<55: return "moderado"
        if s<78: return "alto"
        return "muy alto"
    # Discriminar físico vs emocional
    dfa=_f(dfa_alpha1); rm=_f(rmssd); lf=_f(lf_hf)
    if np.isfinite(dfa) and np.isfinite(rm):
        if dfa<0.75 and rm<30: st="fisico"
        elif dfa>=0.75 and rm<35 and np.isfinite(lf) and lf>2.5: st="emocional"
        elif np.isfinite(lf) and lf>3.0: st="emocional_leve"
        elif dfa<0.75: st="fisico_leve"
        else: st="equilibrado"
    else: st="indeterminado"
    return {"carga_autonomica":{"value":ca,"level":_lv(ca)},"carga_emocional":{"value":ce,"level":_lv(ce)},"carga_fisica":{"value":cf,"level":_lv(cf)},"estres":{"value":es,"level":_lv(es)},"stress_type":st}

# ── Plan de intervención con recomendaciones integrales ───────

PLANES = {
    "optimo":[
        {"item":"Carga fascial y miofascial — máxima intensidad","pct":100},
        {"item":"Ejercicios biomecánicos funcionales de alta demanda","pct":70},
        {"item":"Ejercicios de columna con carga completa","pct":50},
        {"item":"Entrenamiento de fuerza o potencia","pct":60},
        {"item":"Equilibrio SNA — mantenimiento","pct":20},
    ],
    "funcional":[
        {"item":"Tejido miofascial — 60-70% tensión","pct":70},
        {"item":"Equilibrio SNA — respiración, coherencia cardíaca","pct":40},
        {"item":"Ejercicios biomecánicos funcionales","pct":50},
        {"item":"Ejercicios de columna","pct":35},
        {"item":"Stretching activo global","pct":30},
    ],
    "comprometido":[
        {"item":"Equilibrio SNA — patrón respiratorio y coherencia","pct":70},
        {"item":"Tejido miofascial suave — 35-40% tensión","pct":45},
        {"item":"Movilidad articular activo-asistida","pct":30},
        {"item":"Ejercicios de columna — carga baja","pct":20},
        {"item":"Stretching miofascial pasivo","pct":40},
    ],
    "critico":[
        {"item":"Equilibrio SNA intensivo — respiración 4-7-8 y visualización","pct":90},
        {"item":"Tejido miofascial muy suave — sin carga","pct":20},
        {"item":"Movilidad articular pasiva","pct":15},
        {"item":"Relajación progresiva de Jacobson","pct":35},
        {"item":"Evaluación médica si persiste > 48 h","pct":0},
    ],
}

RECS_INTEGRALES = {
    "optimo":{
        "descanso":{"horas":"7-8h","tips":["Mantener horario regular","Exposición solar matutina"]},
        "nutricion":{"suplementos":["Omega-3 1-2 g/día","Vitamina D3 2000 UI"],"alimentos":["Proteína en cada comida","Verduras variadas","35 ml/kg agua"]},
        "meditacion":{"tecnicas":["Coherencia cardíaca 5-5-5 (10 min/día)","Mindfulness 10 min"],"duracion_min":10},
        "actividad":{"tipo":"Alta intensidad permitida","ejemplos":["HIIT","Fuerza máxima","Deporte competitivo"],"frecuencia":"5-6 sesiones/semana"},
        "stretching":{"tecnicas":["Miofascial activo post-sesión","Foam roller cadenas posteriores"],"duracion_min":10},
        "musica":{"recomendacion":"Música motivacional uptempo para sesiones","frecuencias":["432 Hz para recuperación"]},
    },
    "funcional":{
        "descanso":{"horas":"7-9h","tips":["Evitar pantallas 1h antes de dormir","Temperatura 18-20°C"]},
        "nutricion":{"suplementos":["Magnesio 300 mg/día","Omega-3 2 g/día","Vitamina D3 2000 UI"],"alimentos":["Verduras de hoja verde","Frutos secos","Evitar ultraprocesados"]},
        "meditacion":{"tecnicas":["Coherencia cardíaca 6-6 (15 min/día)","Body scan antes de dormir","Respiración diafragmática ante estrés"],"duracion_min":15},
        "actividad":{"tipo":"Moderada-alta intensidad","ejemplos":["Fuerza moderada","Cardio continuo","Yoga dinámico"],"frecuencia":"4-5 sesiones/semana"},
        "stretching":{"tecnicas":["Cadenas miofasciales post. y laterales","Foam roller 60 seg por punto","Psoas y flexores de cadera"],"duracion_min":15},
        "musica":{"recomendacion":"Música clásica barroca o jazz para foco","frecuencias":["432 Hz","Binaural beats alpha 8-12 Hz"]},
    },
    "comprometido":{
        "descanso":{"horas":"8-9h","tips":["Siesta 20 min si es posible","Magnesio bisglicinato 300 mg antes de dormir","Evitar alcohol","Oscuridad total"]},
        "nutricion":{"suplementos":["Magnesio bisglicinato 400 mg/día","Ashwagandha 300-600 mg/día","Complejo B","Omega-3 2-3 g/día","Vitamina C 500 mg/día"],"alimentos":["Fermentados (kéfir, yogur)","Caldo de huesos","Reducir cafeína a <200 mg/día","Evitar alcohol"]},
        "meditacion":{"tecnicas":["Respiración 4-7-8 × 4 ciclos × 3/día","Coherencia cardíaca 6-6 — 15 min/día","NSDR/Yoga Nidra 20 min","Visualización guiada de recuperación","Meditación de compasión"],"duracion_min":25},
        "actividad":{"tipo":"Baja-moderada intensidad","ejemplos":["Caminata 30-45 min","Yoga suave","Pilates","Natación tranquila"],"frecuencia":"3-4 sesiones/semana — FCmax <70%"},
        "stretching":{"tecnicas":["Pasivo mantenido 60-90 seg","Liberación miofascial suave","Foam roller suave zona dorsal","Apertura de cadera supina","Respiración durante el stretching"],"duracion_min":20},
        "musica":{"recomendacion":"Música a 432 Hz y sonidos de naturaleza","frecuencias":["432 Hz — reduce cortisol","Binaural beats theta 4-8 Hz","Isochronic tones 10 Hz alpha"]},
    },
    "critico":{
        "descanso":{"horas":"9h+","tips":["Prioridad máxima","18-20°C y oscuridad total","Evitar alcohol completamente","Magnesio bisglicinato 400 mg","Rutina de relajación 30 min antes"]},
        "nutricion":{"suplementos":["Magnesio bisglicinato 400-500 mg/día","Ashwagandha 600 mg/día","Rhodiola rosea 200-400 mg/día","Complejo B alta potencia","Omega-3 3 g/día","L-teanina 200 mg","Vitamina D3 4000 UI (c/control médico)"],"alimentos":["Dieta antiinflamatoria","Eliminar azúcar refinada","Proteína calidad en cada comida","Máx 1 café por la mañana"]},
        "meditacion":{"tecnicas":["Respiración 4-7-8 × 6 ciclos × 4/día","NSDR/Yoga Nidra 30 min/día","Estimulación nervio vago: tararear, gargarismo, agua fría en cara","Visualización lugar seguro 15 min","EFT/Tapping si hay ansiedad","Coherencia cardíaca 6-6 — 20 min/día"],"duracion_min":40},
        "actividad":{"tipo":"Solo recuperación activa muy suave","ejemplos":["Caminata suave 20-30 min","Tai chi","Yoga restaurativo","Shinrin-yoku (baño de naturaleza)"],"frecuencia":"2-3 sesiones muy suaves/semana"},
        "stretching":{"tecnicas":["Pasivo muy suave 90-120 seg","Respiración 4-7-8 en cada postura","Liberación del diafragma","Relajación progresiva de Jacobson al finalizar"],"duracion_min":25},
        "musica":{"recomendacion":"Musicoterapia como herramienta de recuperación autonómica activa","frecuencias":["528 Hz — regeneración","Binaural beats delta 1-4 Hz","Cuencos tibetanos o crystal bowls","Música gregoriana o mantras"]},
    },
}

STRESS_LABELS = {
    "fisico":"Predominio de fatiga física neuromuscular",
    "fisico_leve":"Leve fatiga física acumulada",
    "emocional":"Predominio de estrés emocional / psicológico",
    "emocional_leve":"Leve activación emocional",
    "equilibrado":"Balance autonómico equilibrado",
    "indeterminado":"Datos insuficientes para discriminar",
}

BIOMARKER_INFO = {
    "RMSSD":{"que_mide":"Variabilidad entre latidos consecutivos. Refleja actividad del nervio vago (parasimpático).","alto":"Excelente tono vagal. Alta capacidad de recuperación.","medio":"Tono vagal normal. Equilibrio autonómico adecuado.","bajo":"Tono vagal reducido. Puede indicar estrés, fatiga o descondicionamiento.","protocolo":"Métrica principal HBA. Corregida por duración y referencia edad/sexo."},
    "lnRMSSD":{"que_mide":"Logaritmo natural del RMSSD. Versión estadísticamente más estable.","alto":">3.9 — excelente variabilidad.","medio":"3.4-3.9 — variabilidad normal.","bajo":"<3.4 — variabilidad reducida.","protocolo":"Útil para comparar entre tests de distinta duración."},
    "SDNN":{"que_mide":"Variabilidad global del ritmo cardíaco. Refleja acción conjunta de simpático y parasimpático.","alto":">60 ms — alta variabilidad global.","medio":"30-60 ms — variabilidad normal.","bajo":"<30 ms — variabilidad reducida. <50 ms en 24h = riesgo cardiovascular.","protocolo":"Complementario al RMSSD."},
    "FC_media":{"que_mide":"Latidos por minuto promedio durante el test.","alto":">85 bpm en reposo — activación simpática o estrés.","medio":"60-85 bpm — rango normal.","bajo":"<60 bpm — bradicardia. Normal en atletas.","protocolo":"FC alta + RMSSD bajo = estrés o fatiga."},
    "LF_HF":{"que_mide":"Balance simpático/parasimpático en dominio frecuencial.","alto":">3.0 — predominio simpático. Estrés o activación.","medio":"1.5-3.0 — balance normal.","bajo":"<1.5 — predominio parasimpático. Relajación profunda.","protocolo":"Solo válido con test ≥5 min. Orientativo en tests cortos."},
    "Baevsky":{"que_mide":"Tensión del sistema regulatorio autonómico. Mayor SI = mayor esfuerzo del SNA.","alto":">150 — tensión elevada. >300 = estrés agudo.","medio":"50-150 — tensión normal.","bajo":"<50 — estado óptimo, alta variabilidad.","protocolo":"Disponible solo con sensores que proveen RR (Polar/import)."},
    "SD1":{"que_mide":"Variabilidad latido a latido. Correlaciona directamente con RMSSD y actividad vagal.","alto":">30 ms — excelente tono vagal.","medio":"15-30 ms — normal.","bajo":"<15 ms — tono vagal reducido.","protocolo":"SD1 = RMSSD/√2. Visualización del Poincaré."},
    "SD2":{"que_mide":"Variabilidad a largo plazo en el diagrama de Poincaré.","alto":">60 ms — alta variabilidad global.","medio":"30-60 ms — normal.","bajo":"<30 ms — baja variabilidad, posible fatiga crónica.","protocolo":"SD1/SD2 <0.5 indica predominio simpático."},
    "DFA_a1":{"que_mide":"Correlaciones fractales corto plazo. Complejidad autonómica.","alto":"1.0-1.5 — fractalidad saludable, normal.","medio":"0.75-1.0 — leve alteración.","bajo":"<0.75 — desregulación autonómica, fatiga física acumulada.","protocolo":"Discriminador clave: DFA<0.75+RMSSD bajo=fatiga física. DFA normal+RMSSD bajo+LF/HF alto=estrés emocional."},
}

# ── Dashboard enriquecido ─────────────────────────────────────

def _hml(value, low, high):
    v=_f(value)
    if not np.isfinite(v): return "insuficiente"
    if v<low: return "bajo"
    if v>high: return "alto"
    return "medio"

def enrich_dashboard(result, payload):
    if result.get("error"): return result
    age=payload.get("age"); sex=payload.get("sex")
    rmssd=_f(result.get("rmssd")); rmssd_corr=_f(result.get("rmssd_corr",result.get("rmssd")))
    sdnn=_f(result.get("sdnn")); lnrmssd=_f(result.get("lnrmssd")); pnn50=_f(result.get("pnn50"))
    lfhf=_f(result.get("lf_hf")); hr_mean=_f(result.get("hr_mean"))
    sd1=_f(result.get("sd1")); sd2=_f(result.get("sd2"))
    dfa1=_f(result.get("dfa_alpha1")); baevsky=_f(result.get("baevsky"))
    rm_low,rm_high=rmssd_reference(age,sex)
    rm_state=_hml(rmssd_corr,rm_low,rm_high)
    cargas=compute_cargas(rmssd_corr,sdnn,pnn50,lfhf,hr_mean,baevsky,sd1,dfa1)
    ca_score=cargas["carga_autonomica"]["value"]
    stress_type=cargas.get("stress_type","indeterminado")
    sem_key=classify_semaphore(rmssd_corr,rm_low,rm_high,ca_score)
    sem_data=SEMAPHORE[sem_key]
    recs=RECS_INTEGRALES.get(sem_key, RECS_INTEGRALES["funcional"])
    # Nota extra si hay estrés emocional
    if stress_type in ("emocional","emocional_leve"):
        recs["nota_stress"]="Tu HRV indica predominio de estrés emocional/psicológico. Las técnicas vagales y coherencia cardíaca son especialmente indicadas. Considerá apoyo psicológico si persiste."
    elif stress_type in ("fisico","fisico_leve"):
        recs["nota_stress"]="Tu HRV indica predominio de fatiga física acumulada. Priorizá descanso y recuperación activa. El sueño es tu mejor herramienta de recuperación ahora."
    biomarkers=[
        {"name":"RMSSD","value":rmssd,"unit":"ms","state":rm_state,"detail":f"Ref: {rm_low:.0f}–{rm_high:.0f} ms | Corregido: {rmssd_corr:.1f} ms","info":BIOMARKER_INFO["RMSSD"]},
        {"name":"lnRMSSD","value":lnrmssd,"unit":"","state":"informativo","detail":"Logaritmo natural RMSSD corregido","info":BIOMARKER_INFO["lnRMSSD"]},
        {"name":"SDNN","value":sdnn,"unit":"ms","state":_hml(sdnn,30,60),"detail":"Variabilidad global","info":BIOMARKER_INFO["SDNN"]},
        {"name":"FC media","value":hr_mean,"unit":"bpm","state":_hml(hr_mean,60,85),"detail":"Frecuencia cardíaca promedio","info":BIOMARKER_INFO["FC_media"]},
        {"name":"LF/HF","value":lfhf,"unit":"","state":_hml(lfhf,1.5,3.0),"detail":result.get("freq_warning") or "Balance simpático/parasimpático","info":BIOMARKER_INFO["LF_HF"]},
        {"name":"Baevsky (SI)","value":baevsky,"unit":"","state":_hml(baevsky,50,150),"detail":"Tensión sistema regulatorio autonómico","info":BIOMARKER_INFO["Baevsky"]},
        {"name":"SD1 (Poincaré)","value":sd1,"unit":"ms","state":_hml(sd1,15,40),"detail":"Variabilidad corto plazo — vagal","info":BIOMARKER_INFO["SD1"]},
        {"name":"SD2 (Poincaré)","value":sd2,"unit":"ms","state":_hml(sd2,30,70),"detail":"Variabilidad largo plazo","info":BIOMARKER_INFO["SD2"]},
        {"name":"DFA α1","value":dfa1,"unit":"","state":_hml(dfa1,0.75,1.5),"detail":"<0.75=fatiga física | Normal+LF/HF alto=estrés emocional","info":BIOMARKER_INFO["DFA_a1"]},
    ]
    result["hba_dashboard"]={
        "biomarkers":biomarkers,"cargas":cargas,
        "norms":{"age":age,"sex":sex,"rmssd_low":rm_low,"rmssd_high":rm_high,"rmssd_state":rm_state},
        "semaphore":{"key":sem_key,"label":sem_data["label"],"color":sem_data["color"],"color_light":sem_data["color_light"],"icon":sem_data["icon"],"description":sem_data["description"]},
        "plan":PLANES.get(sem_key,PLANES["funcional"]),
        "recomendaciones":recs,
        "stress_type":stress_type,
        "stress_label":STRESS_LABELS.get(stress_type,"—"),
    }
    return result

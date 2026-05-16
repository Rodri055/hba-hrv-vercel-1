import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

from flask import Flask, send_from_directory, request
from hrv_core import (
    compute_hrv_from_rri, compute_hrv_from_ppg,
    enrich_dashboard, sanitize_for_json,
)
import json, numpy as np, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
BASE_DIR = "/var/task" if os.path.exists("/var/task/app.py") else os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")
CORS = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST,GET,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Content-Type":"application/json"}

# ── Supabase via REST API (sin librería externa) ──────────────

def _sb_insert(row):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False, "none_configured"
    clean = {}
    for k, v in row.items():
        if v is None: continue
        if isinstance(v, float) and (v != v): continue  # NaN
        clean[k] = v
    url = f"{SUPABASE_URL}/rest/v1/hba_sessions"
    body = json.dumps(clean).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Prefer", "return=minimal")
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True, "supabase"
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")
        return False, f"http_{e.code}: {err}"
    except Exception as ex:
        return False, str(ex)

def _sb_query(patient_id):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return [], "none_configured"
    pid = urllib.parse.quote(str(patient_id))
    url = f"{SUPABASE_URL}/rest/v1/hba_sessions?patient_id=eq.{pid}&order=timestamp_utc.desc&limit=100"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_KEY}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode()), "supabase"
    except Exception as ex:
        return [], str(ex)

# ── Rutas ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/static/manifest.json")
def manifest():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "manifest.json", mimetype="application/manifest+json")

@app.route("/api/compute", methods=["POST","OPTIONS"])
def compute():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS)
    try:
        payload = request.get_json(force=True) or {}
    except:
        return app.response_class(json.dumps({"error":"JSON inválido"}), status=400, headers=CORS)

    sensor_type      = str(payload.get("sensor_type","")).strip()
    duration_minutes = payload.get("duration_minutes")

    if sensor_type in ("polar_h10","rr_upload"):
        rri_ms = payload.get("rri_ms",[])
        if not rri_ms or len(rri_ms) < 12:
            return app.response_class(json.dumps({"error":"rri_ms insuficiente."}), status=400, headers=CORS)
        result = compute_hrv_from_rri(np.array(rri_ms, dtype=float), duration_minutes=duration_minutes, sensor_type=sensor_type)
    elif sensor_type in ("camera_ppg","face_rppg","vibration_scg"):
        ppg = payload.get("ppg",[])
        sr  = float(payload.get("sampling_rate", 30))
        if not ppg or len(ppg) < 100:
            return app.response_class(json.dumps({"error":"ppg insuficiente."}), status=400, headers=CORS)
        result = compute_hrv_from_ppg(np.array(ppg, dtype=float), sr, duration_minutes=duration_minutes, sensor_type=sensor_type)
    else:
        return app.response_class(json.dumps({"error":"sensor_type inválido."}), status=400, headers=CORS)

    result["sensor_type"]      = sensor_type
    result["duration_minutes"] = duration_minutes
    result = enrich_dashboard(result, payload)
    return app.response_class(json.dumps(sanitize_for_json(result)), status=200, headers=CORS)

@app.route("/api/save", methods=["POST","OPTIONS"])
def save():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS)
    try:
        payload = request.get_json(force=True) or {}
    except:
        return app.response_class(json.dumps({"error":"JSON inválido"}), status=400, headers=CORS)

    metrics = payload.get("metrics", {}) or {}
    dash    = metrics.get("hba_dashboard", {}) or {}
    cargas  = dash.get("cargas", {}) or {}
    sem     = dash.get("semaphore", {}) or {}

    def _v(d, *keys):
        v = d
        for k in keys:
            if not isinstance(v, dict): return None
            v = v.get(k)
        return v if v != "" else None

    row = {
        "timestamp_utc":    datetime.now(timezone.utc).isoformat(),
        "patient_id":       str(payload.get("patient_id","")).strip() or None,
        "age":              payload.get("age") or None,
        "sex":              str(payload.get("sex","")).strip().upper() or None,
        "comorbidities":    str(payload.get("comorbidities","")).strip() or None,
        "notes":            str(payload.get("notes","")).strip() or None,
        "sensor_type":      metrics.get("sensor_type"),
        "duration_minutes": metrics.get("duration_minutes"),
        "rmssd":            metrics.get("rmssd"),
        "rmssd_corr":       metrics.get("rmssd_corr"),
        "sdnn":             metrics.get("sdnn"),
        "lnrmssd":          metrics.get("lnrmssd"),
        "pnn50":            metrics.get("pnn50"),
        "mean_rr":          metrics.get("mean_rr"),
        "lf_power":         metrics.get("lf_power"),
        "hf_power":         metrics.get("hf_power"),
        "lf_hf":            metrics.get("lf_hf"),
        "sd1":              metrics.get("sd1"),
        "sd2":              metrics.get("sd2"),
        "dfa_alpha1":       metrics.get("dfa_alpha1"),
        "baevsky":          metrics.get("baevsky"),
        "artifact_percent": metrics.get("artifact_percent"),
        "quality_score":    metrics.get("quality_score"),
        "hr_mean":          metrics.get("hr_mean"),
        "hr_max":           metrics.get("hr_max"),
        "hr_min":           metrics.get("hr_min"),
        "carga_autonomica": _v(cargas,"carga_autonomica","value"),
        "carga_emocional":  _v(cargas,"carga_emocional","value"),
        "carga_fisica":     _v(cargas,"carga_fisica","value"),
        "estres":           _v(cargas,"estres","value"),
        "semaphore_key":    sem.get("key"),
        "semaphore_label":  sem.get("label"),
        "stress_type":      dash.get("stress_type"),
    }

    ok, backend = _sb_insert(row)
    return app.response_class(
        json.dumps({"ok": ok, "backend": backend}),
        status=200, headers=CORS
    )

@app.route("/api/history", methods=["GET","OPTIONS"])
def history():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS)
    patient_id = request.args.get("patient_id","").strip()
    if not patient_id:
        return app.response_class(json.dumps({"error":"patient_id requerido"}), status=400, headers=CORS)
    data, backend = _sb_query(patient_id)
    return app.response_class(
        json.dumps({"data": data, "backend": backend}),
        status=200, headers=CORS
    )

if __name__ == "__main__":
    app.run(debug=True)

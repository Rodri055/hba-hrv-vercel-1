"""
HBA v2.0 — api/save.py
Vercel Python: objeto `app` Flask como WSGI entry point.
POST /api/save — persiste sesión en Supabase.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json
from datetime import datetime, timezone
from flask import Flask, request

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}

def _sb():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

def _v(d, *keys):
    v = d
    for k in keys:
        if not isinstance(v, dict): return None
        v = v.get(k)
    return v if v != "" else None

@app.route("/api/save", methods=["POST", "OPTIONS"])
def save():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS)

    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return app.response_class(json.dumps({"error": "JSON inválido"}), status=400, headers=CORS)

    metrics = payload.get("metrics", {}) or {}
    dash    = metrics.get("hba_dashboard", {}) or {}
    cargas  = dash.get("cargas", {}) or {}
    sem     = dash.get("semaphore", {}) or {}

    row = {
        "timestamp_utc":    datetime.now(timezone.utc).isoformat(),
        "patient_id":       str(payload.get("patient_id", "")).strip() or None,
        "age":              payload.get("age") or None,
        "sex":              str(payload.get("sex", "")).strip().upper() or None,
        "comorbidities":    str(payload.get("comorbidities", "")).strip() or None,
        "notes":            str(payload.get("notes", "")).strip() or None,
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
        "total_power":      metrics.get("total_power"),
        "sd1":              metrics.get("sd1"),
        "sd2":              metrics.get("sd2"),
        "sd1_sd2_ratio":    metrics.get("sd1_sd2_ratio"),
        "dfa_alpha1":       metrics.get("dfa_alpha1"),
        "artifact_percent": metrics.get("artifact_percent"),
        "quality_score":    metrics.get("quality_score"),
        "hr_mean":          metrics.get("hr_mean"),
        "hr_max":           metrics.get("hr_max"),
        "hr_min":           metrics.get("hr_min"),
        "resp_rate_rpm":    metrics.get("resp_rate_rpm"),
        "carga_autonomica": _v(cargas, "carga_autonomica", "value"),
        "carga_emocional":  _v(cargas, "carga_emocional",  "value"),
        "carga_fisica":     _v(cargas, "carga_fisica",     "value"),
        "estres":           _v(cargas, "estres",           "value"),
        "semaphore_key":    sem.get("key"),
        "semaphore_label":  sem.get("label"),
        "freq_warning":     metrics.get("freq_warning"),
    }

    sb = _sb()
    if sb:
        try:
            sb.table("hba_sessions").insert(row).execute()
            backend = "supabase"
        except Exception as e:
            return app.response_class(
                json.dumps({"ok": False, "error": str(e)}), status=500, headers=CORS
            )
    else:
        backend = "none_configured"

    return app.response_class(
        json.dumps({"ok": True, "backend": backend}), status=200, headers=CORS
    )

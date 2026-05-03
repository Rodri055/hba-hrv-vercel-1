"""
HBA v2.0 — api/save.py
Función serverless Vercel: persiste una sesión en Supabase.
"""

import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def _get_sb():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None


def handler(request, response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    if request.method == "OPTIONS":
        response.status_code = 204
        return response

    try:
        payload = request.json or {}
    except Exception:
        response.status_code = 400
        return response.send(json.dumps({"error": "JSON inválido"}))

    metrics = payload.get("metrics", {}) or {}
    dash    = metrics.get("hba_dashboard", {}) or {}
    cargas  = dash.get("cargas", {}) or {}
    sem     = dash.get("semaphore", {}) or {}

    def _c(d, *keys, default=""):
        """Navegar dict anidado con fallback."""
        v = d
        for k in keys:
            if not isinstance(v, dict):
                return default
            v = v.get(k, default)
        return v if v is not None else default

    row = {
        "timestamp_utc":    datetime.now(timezone.utc).isoformat(),
        "patient_id":       str(payload.get("patient_id", "")).strip(),
        "age":              payload.get("age") or None,
        "sex":              str(payload.get("sex", "")).strip().upper() or None,
        "comorbidities":    str(payload.get("comorbidities", "")).strip() or None,
        "notes":            str(payload.get("notes", "")).strip() or None,
        "sensor_type":      metrics.get("sensor_type") or None,
        "duration_minutes": metrics.get("duration_minutes") or None,
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
        "carga_autonomica": _c(cargas, "carga_autonomica", "value"),
        "carga_emocional":  _c(cargas, "carga_emocional",  "value"),
        "carga_fisica":     _c(cargas, "carga_fisica",     "value"),
        "estres":           _c(cargas, "estres",           "value"),
        "semaphore_key":    sem.get("key") or None,
        "semaphore_label":  sem.get("label") or None,
        "freq_warning":     metrics.get("freq_warning") or None,
    }

    # Limpiar None en valores numéricos para Supabase
    for k in ["age", "duration_minutes", "rmssd", "rmssd_corr", "sdnn",
              "lnrmssd", "pnn50", "mean_rr", "lf_power", "hf_power",
              "lf_hf", "total_power", "sd1", "sd2", "sd1_sd2_ratio",
              "dfa_alpha1", "artifact_percent", "quality_score",
              "hr_mean", "hr_max", "hr_min", "resp_rate_rpm",
              "carga_autonomica", "carga_emocional", "carga_fisica", "estres"]:
        v = row.get(k)
        if v == "" or v != v:  # NaN check
            row[k] = None

    sb = _get_sb()
    if sb:
        try:
            sb.table("hba_sessions").insert(row).execute()
            backend = "supabase"
        except Exception as e:
            response.status_code = 500
            return response.send(json.dumps({"ok": False, "error": str(e)}))
    else:
        # Sin Supabase configurado — devolver ok igual (datos en cliente)
        backend = "none_configured"

    response.status_code = 200
    response.headers["Content-Type"] = "application/json"
    return response.send(json.dumps({"ok": True, "backend": backend}))

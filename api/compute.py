"""
HBA v2.0 — api/compute.py
Función serverless Vercel: recibe señal, devuelve HRV + dashboard.
"""

import json
import sys
import os

# Vercel corre desde /var/task — agregar api/ al path para hrv_core
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from hrv_core import (
    compute_hrv_from_rri,
    compute_hrv_from_ppg,
    enrich_dashboard,
    sanitize_for_json,
)


def handler(request, response):
    # CORS
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    if request.method == "OPTIONS":
        response.status_code = 204
        return response

    if request.method != "POST":
        response.status_code = 405
        return response.send(json.dumps({"error": "Método no permitido"}))

    try:
        payload = request.json or {}
    except Exception:
        response.status_code = 400
        return response.send(json.dumps({"error": "JSON inválido"}))

    sensor_type      = str(payload.get("sensor_type", "")).strip()
    duration_minutes = payload.get("duration_minutes")

    if sensor_type in ("polar_h10", "rr_upload"):
        rri_ms = payload.get("rri_ms", [])
        if not rri_ms or len(rri_ms) < 12:
            response.status_code = 400
            return response.send(json.dumps({"error": "rri_ms insuficiente (mínimo 12 valores)."}))
        result = compute_hrv_from_rri(np.array(rri_ms, dtype=float), duration_minutes=duration_minutes)

    elif sensor_type in ("camera_ppg", "face_rppg", "vibration_scg"):
        ppg = payload.get("ppg", [])
        sampling_rate = float(payload.get("sampling_rate", 30))
        if not ppg or len(ppg) < 100:
            response.status_code = 400
            return response.send(json.dumps({"error": "ppg insuficiente."}))
        result = compute_hrv_from_ppg(np.array(ppg, dtype=float), sampling_rate, duration_minutes=duration_minutes)

    else:
        response.status_code = 400
        return response.send(json.dumps({"error": "sensor_type inválido. Use: polar_h10, rr_upload, camera_ppg, face_rppg, vibration_scg"}))

    result["sensor_type"]      = sensor_type
    result["duration_minutes"] = duration_minutes
    result = enrich_dashboard(result, payload)

    response.status_code = 200
    response.headers["Content-Type"] = "application/json"
    return response.send(json.dumps(sanitize_for_json(result)))

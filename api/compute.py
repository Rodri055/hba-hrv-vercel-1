"""
HBA v2.0 — api/compute.py
Vercel Python: objeto `app` Flask como WSGI entry point.
POST /api/compute — recibe señal, devuelve HRV + dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import numpy as np
from flask import Flask, request
from hrv_core import (
    compute_hrv_from_rri,
    compute_hrv_from_ppg,
    enrich_dashboard,
    sanitize_for_json,
)

app = Flask(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}


@app.route("/api/compute", methods=["POST", "OPTIONS"])
def compute():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS_HEADERS)

    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return app.response_class(
            json.dumps({"error": "JSON inválido"}), status=400, headers=CORS_HEADERS
        )

    sensor_type      = str(payload.get("sensor_type", "")).strip()
    duration_minutes = payload.get("duration_minutes")

    if sensor_type in ("polar_h10", "rr_upload"):
        rri_ms = payload.get("rri_ms", [])
        if not rri_ms or len(rri_ms) < 12:
            return app.response_class(
                json.dumps({"error": "rri_ms insuficiente (mínimo 12 valores)."}),
                status=400, headers=CORS_HEADERS
            )
        result = compute_hrv_from_rri(
            np.array(rri_ms, dtype=float), duration_minutes=duration_minutes
        )

    elif sensor_type in ("camera_ppg", "face_rppg", "vibration_scg"):
        ppg = payload.get("ppg", [])
        sampling_rate = float(payload.get("sampling_rate", 30))
        if not ppg or len(ppg) < 100:
            return app.response_class(
                json.dumps({"error": "ppg insuficiente."}),
                status=400, headers=CORS_HEADERS
            )
        result = compute_hrv_from_ppg(
            np.array(ppg, dtype=float), sampling_rate, duration_minutes=duration_minutes
        )

    else:
        return app.response_class(
            json.dumps({"error": "sensor_type inválido."}),
            status=400, headers=CORS_HEADERS
        )

    result["sensor_type"]      = sensor_type
    result["duration_minutes"] = duration_minutes
    result = enrich_dashboard(result, payload)

    return app.response_class(
        json.dumps(sanitize_for_json(result)), status=200, headers=CORS_HEADERS
    )

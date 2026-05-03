"""
HBA v2.0 — api/history.py
Historial de sesiones por patient_id desde Supabase.
"""

import json
import os
import sys

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


def handler(request, response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    if request.method == "OPTIONS":
        response.status_code = 204
        return response

    patient_id = (request.args or {}).get("patient_id", "").strip()
    if not patient_id:
        response.status_code = 400
        return response.send(json.dumps({"error": "patient_id requerido"}))

    if not SUPABASE_URL or not SUPABASE_KEY:
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        return response.send(json.dumps({"data": [], "warning": "Supabase no configurado"}))

    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = (sb.table("hba_sessions")
               .select("*")
               .eq("patient_id", patient_id)
               .order("timestamp_utc", desc=True)
               .limit(100)
               .execute())
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        return response.send(json.dumps({"data": res.data or []}))
    except Exception as e:
        response.status_code = 500
        return response.send(json.dumps({"error": str(e)}))

"""
HBA v2.0 — api/history.py
Vercel Python: objeto `app` Flask como WSGI entry point.
GET /api/history?patient_id=X — historial desde Supabase.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json
from flask import Flask, request

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json",
}

@app.route("/api/history", methods=["GET", "OPTIONS"])
def history():
    if request.method == "OPTIONS":
        return app.response_class("", status=204, headers=CORS)

    patient_id = request.args.get("patient_id", "").strip()
    if not patient_id:
        return app.response_class(
            json.dumps({"error": "patient_id requerido"}), status=400, headers=CORS
        )

    if not SUPABASE_URL or not SUPABASE_KEY:
        return app.response_class(
            json.dumps({"data": [], "warning": "Supabase no configurado"}),
            status=200, headers=CORS
        )

    try:
        from supabase import create_client
        sb  = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = (sb.table("hba_sessions")
               .select("*")
               .eq("patient_id", patient_id)
               .order("timestamp_utc", desc=True)
               .limit(100)
               .execute())
        return app.response_class(
            json.dumps({"data": res.data or []}), status=200, headers=CORS
        )
    except Exception as e:
        return app.response_class(
            json.dumps({"error": str(e)}), status=500, headers=CORS
        )

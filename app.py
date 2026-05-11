import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

from flask import Flask, send_from_directory, request
from hrv_core import (
    compute_hrv_from_rri, compute_hrv_from_ppg,
    enrich_dashboard, sanitize_for_json,
)
import json, numpy as np
from datetime import datetime, timezone

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
BASE_DIR = "/var/task" if os.path.exists("/var/task/app.py") else os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")

CORS = {"Access-Control-Allow-Origin":"*","Access-Control-Allow-Methods":"POST,GET,OPTIONS","Access-Control-Allow-Headers":"Content-Type","Content-Type":"application/json"}

def _sb():
    if not SUPABASE_URL or not SUPABASE_KEY: return None
    try:
        from supabase import create_client
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/static/manifest.json")
def manifest():
    return send_from_directory(os.path.join(BASE_DIR,"static"), "manifest.json", mimetype="application/manifest+json")

@app.route("/api/compute", methods=["POST","OPTIONS"])
def compute():
    if request.method=="OPTIONS": return app.response_class("",status=204,headers=CORS)
    try: payload=request.get_json(force=True) or {}
    except: return app.response_class(json.dumps({"error":"JSON inválido"}),status=400,headers=CORS)

    sensor_type      = str(payload.get("sensor_type","")).strip()
    duration_minutes = payload.get("duration_minutes")

    if sensor_type in ("polar_h10","rr_upload"):
        rri_ms = payload.get("rri_ms",[])
        if not rri_ms or len(rri_ms)<12:
            return app.response_class(json.dumps({"error":"rri_ms insuficiente."}),status=400,headers=CORS)
        result = compute_hrv_from_rri(np.array(rri_ms,dtype=float), duration_minutes=duration_minutes, sensor_type=sensor_type)

    elif sensor_type in ("camera_ppg","face_rppg","vibration_scg"):
        ppg = payload.get("ppg",[])
        sr  = float(payload.get("sampling_rate",30))
        if not ppg or len(ppg)<100:
            return app.response_class(json.dumps({"error":"ppg insuficiente."}),status=400,headers=CORS)
        result = compute_hrv_from_ppg(np.array(ppg,dtype=float), sr, duration_minutes=duration_minutes, sensor_type=sensor_type)
    else:
        return app.response_class(json.dumps({"error":"sensor_type inválido."}),status=400,headers=CORS)

    result["sensor_type"]=sensor_type; result["duration_minutes"]=duration_minutes
    result=enrich_dashboard(result,payload)
    return app.response_class(json.dumps(sanitize_for_json(result)),status=200,headers=CORS)

@app.route("/api/save", methods=["POST","OPTIONS"])
def save():
    if request.method=="OPTIONS": return app.response_class("",status=204,headers=CORS)
    try: payload=request.get_json(force=True) or {}
    except: return app.response_class(json.dumps({"error":"JSON inválido"}),status=400,headers=CORS)
    metrics=payload.get("metrics",{}) or {}
    dash=metrics.get("hba_dashboard",{}) or {}
    cargas=dash.get("cargas",{}) or {}
    sem=dash.get("semaphore",{}) or {}
    def _v(d,*keys):
        v=d
        for k in keys:
            if not isinstance(v,dict): return None
            v=v.get(k)
        return v if v!="" else None
    row={
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "patient_id":str(payload.get("patient_id","")).strip() or None,
        "age":payload.get("age") or None,"sex":str(payload.get("sex","")).strip().upper() or None,
        "comorbidities":str(payload.get("comorbidities","")).strip() or None,
        "notes":str(payload.get("notes","")).strip() or None,
        "sensor_type":metrics.get("sensor_type"),"duration_minutes":metrics.get("duration_minutes"),
        "rmssd":metrics.get("rmssd"),"rmssd_corr":metrics.get("rmssd_corr"),
        "sdnn":metrics.get("sdnn"),"lnrmssd":metrics.get("lnrmssd"),"pnn50":metrics.get("pnn50"),
        "mean_rr":metrics.get("mean_rr"),"lf_power":metrics.get("lf_power"),
        "hf_power":metrics.get("hf_power"),"lf_hf":metrics.get("lf_hf"),
        "sd1":metrics.get("sd1"),"sd2":metrics.get("sd2"),
        "dfa_alpha1":metrics.get("dfa_alpha1"),"baevsky":metrics.get("baevsky"),
        "artifact_percent":metrics.get("artifact_percent"),"quality_score":metrics.get("quality_score"),
        "hr_mean":metrics.get("hr_mean"),"hr_max":metrics.get("hr_max"),"hr_min":metrics.get("hr_min"),
        "carga_autonomica":_v(cargas,"carga_autonomica","value"),
        "carga_emocional":_v(cargas,"carga_emocional","value"),
        "carga_fisica":_v(cargas,"carga_fisica","value"),
        "estres":_v(cargas,"estres","value"),
        "semaphore_key":sem.get("key"),"semaphore_label":sem.get("label"),
        "stress_type":dash.get("stress_type"),
    }
    sb=_sb()
    if sb:
        try: sb.table("hba_sessions").insert(row).execute(); backend="supabase"
        except Exception as e: return app.response_class(json.dumps({"ok":False,"error":str(e)}),status=500,headers=CORS)
    else: backend="none_configured"
    return app.response_class(json.dumps({"ok":True,"backend":backend}),status=200,headers=CORS)

@app.route("/api/history", methods=["GET","OPTIONS"])
def history():
    if request.method=="OPTIONS": return app.response_class("",status=204,headers=CORS)
    patient_id=request.args.get("patient_id","").strip()
    if not patient_id: return app.response_class(json.dumps({"error":"patient_id requerido"}),status=400,headers=CORS)
    sb=_sb()
    if not sb: return app.response_class(json.dumps({"data":[]}),status=200,headers=CORS)
    try:
        res=sb.table("hba_sessions").select("*").eq("patient_id",patient_id).order("timestamp_utc",desc=True).limit(100).execute()
        return app.response_class(json.dumps({"data":res.data or []}),status=200,headers=CORS)
    except Exception as e: return app.response_class(json.dumps({"error":str(e)}),status=500,headers=CORS)

if __name__=="__main__":
    app.run(debug=True)

"""
HANNA · hba_report/routes.py
Endpoints del informe PDF. ACCESO PROTEGIDO en el servidor:

  GET  /api/report/status  -> {"enabled": bool}              (no revela la contraseña)
  POST /api/report         -> application/pdf                (exige la cabecera X-Report-Key)

La contraseña se define en la variable de entorno REPORT_PASSWORD. Si no está definida, el endpoint queda
DESHABILITADO (seguro por defecto). La verificación vive en authorize(): para pasar a un esquema arancelado
(pago previo, token, etc.) solo hay que reemplazar esa función.

Privacidad: el PDF se genera en memoria y se devuelve; no se guarda en disco ni en servicios externos, y los
datos del paciente no se escriben en los logs.
"""
import hmac
import os
import re
import time
from urllib.parse import unquote

from flask import Blueprint, Response, jsonify, request

bp = Blueprint("report", __name__)

MAX_BODY = 2 * 1024 * 1024          # 2 MB: sobra para una medición + historial + serie RR
MAX_FAILS, WINDOW = 8, 600           # 8 intentos fallidos cada 10 min por IP (mejor esfuerzo; ver README)
_fails = {}                          # ip -> [cantidad, inicio de ventana]


def _ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() or request.remote_addr or "?")[:64]


def _blocked(ip):
    rec = _fails.get(ip)
    if not rec:
        return False
    if time.time() - rec[1] > WINDOW:
        _fails.pop(ip, None)
        return False
    return rec[0] >= MAX_FAILS


def authorize(req):
    """Devuelve (ok, status_http, mensaje). Punto único de control de acceso."""
    expected = os.environ.get("REPORT_PASSWORD", "")
    if not expected:
        return False, 503, "El informe PDF no está habilitado en este servidor (falta configurar REPORT_PASSWORD)."
    ip = _ip()
    if _blocked(ip):
        return False, 429, "Demasiados intentos fallidos. Esperá unos minutos y volvé a intentar."
    supplied = unquote(req.headers.get("X-Report-Key", ""))   # el navegador la envía codificada (cabeceras = Latin-1)
    if hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
        _fails.pop(ip, None)
        return True, 200, ""
    rec = _fails.setdefault(ip, [0, time.time()])
    rec[0] += 1
    time.sleep(0.7)                  # frena la fuerza bruta
    return False, 401, "Contraseña incorrecta."


def _json(status, **body):
    r = jsonify(body)
    r.status_code = status
    r.headers["Cache-Control"] = "no-store"
    return r


@bp.route("/api/report/status", methods=["GET"])
def status():
    return _json(200, enabled=bool(os.environ.get("REPORT_PASSWORD")))


@bp.route("/api/report", methods=["POST"])
def make_report():
    ok, code, msg = authorize(request)
    if not ok:
        return _json(code, error=msg)
    if (request.content_length or 0) > MAX_BODY:
        return _json(413, error="Los datos enviados son demasiado grandes.")
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return _json(400, error="JSON inválido.")
    if not isinstance(payload, dict) or not isinstance(payload.get("metrics"), dict):
        return _json(400, error="Faltan los resultados de la medición (metrics).")
    try:
        from .engine import build_model
        from .pdf import build_pdf
        model = build_model(payload)
        pdf = build_pdf(model)
    except ValueError as e:
        return _json(422, error=str(e))
    except Exception:
        return _json(500, error="No se pudo generar el informe.")
    when = model["when_dt"].strftime("%Y%m%d")
    pid = re.sub(r"[^A-Za-z0-9_-]+", "", model["patient"]["id"])[:24] or "paciente"
    resp = Response(pdf, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = f'attachment; filename="informe-hrv-{pid}-{when}.pdf"'
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return resp

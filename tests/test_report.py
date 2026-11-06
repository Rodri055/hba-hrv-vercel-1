"""
Pruebas del módulo de informes PDF (sin dependencias extra: unittest).
Ejecutar desde la raíz del proyecto:   python -m unittest discover -s tests -v
"""
import io
import json
import os
import sys
import unittest
from unittest import mock
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))

from app import app                     # noqa: E402
from hba_report import draw, routes         # noqa: E402
from hba_report.engine import build_model   # noqa: E402
from hba_report.pdf import build_pdf        # noqa: E402

METRICS = {"sensor_type": "polar_h10", "duration_minutes": 5, "rmssd": 38.4, "rmssd_corr": 38.4, "sdnn": 43.6, "hr_mean": 71,
           "pnn50": 20.7, "lf_hf": 1.05, "lf_power": 0.0052, "hf_power": 0.0049, "sd1": 27.2, "sd2": 55.2, "dfa_alpha1": 0.99,
           "baevsky": 21, "quality_score": 100, "artifact_percent": 0.0, "mean_rr": 845}


def page_count(pdf):
    try:
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(pdf)).pages)
    except ImportError:
        return pdf.count(b"/Type /Page\n") or pdf.count(b"/Type /Page")


class Engine(unittest.TestCase):
    def test_no_inventa_indicadores(self):
        m = build_model({"patient_id": "X", "metrics": {"sensor_type": "vibration_scg", "duration_minutes": 1, "rmssd": 28.5, "hr_mean": 74}})
        self.assertEqual({r["key"] for r in m["indicators"]}, {"hr_mean", "rmssd"})

    def test_sin_indicadores_falla(self):
        with self.assertRaises(ValueError):
            build_model({"patient_id": "X", "metrics": {"sensor_type": "polar_h10"}})

    def test_senal_invalida_no_se_interpreta(self):
        m = build_model({"patient_id": "X", "age": 40, "sex": "M", "metrics": {"sensor_type": "camera_ppg", "duration_minutes": 3, "rmssd": 1.2, "hr_mean": 72, "artifact_percent": 65}})
        self.assertEqual(m["alerts"]["severity"], "invalid")
        self.assertTrue(all(r["state"] == "invalid" and r["color"] == "red" for r in m["indicators"]))
        self.assertEqual(m["plan"]["next"][0], "En 24–48 horas")

    def test_potencias_absolutas_no_se_muestran(self):
        m = build_model({"patient_id": "X", "metrics": METRICS})
        keys = {r["key"] for r in m["indicators"]}
        self.assertFalse(keys & {"lf_power", "hf_power", "total_power"})
        self.assertIn("hf_share", keys)

    def test_edad_ausente_se_declara(self):
        m = build_model({"patient_id": "X", "metrics": METRICS})
        self.assertIn("No se registró la edad", m["summary"])

    def test_comorbilidad_modera_ejercicio_pero_no_posterga_evaluacion(self):
        m = build_model({"patient_id": "X", "age": 40, "sex": "F", "comorbidities": "HTA", "metrics": METRICS})
        self.assertTrue(m["plan"]["prof_first"])
        self.assertFalse(m["plan"]["eval_first"])
        self.assertEqual(m["plan"]["next"][0], "En 7 días")

    def test_fc_extrema_exige_evaluacion(self):
        m = build_model({"patient_id": "X", "age": 40, "metrics": dict(METRICS, hr_mean=112)})
        self.assertTrue(m["plan"]["eval_first"])

    def test_estados_coinciden_con_la_app(self):
        from hrv_core import _hml
        m = build_model({"patient_id": "X", "age": 40, "sex": "F", "metrics": METRICS})
        mp = {"low": "bajo", "high": "alto", "in": "medio"}
        for k, (lo, hi) in {"sdnn": (30, 60), "hr_mean": (60, 85), "lf_hf": (1.5, 3.0), "sd1": (15, 40), "sd2": (30, 70), "dfa_alpha1": (0.75, 1.5), "baevsky": (50, 150)}.items():
            r = next((x for x in m["indicators"] if x["key"] == k), None)
            if r:
                self.assertEqual(mp[r["state"]], _hml(r["value"], lo, hi), k)

    def test_historial_y_linea_base(self):
        base = {"patient_id": "X", "age": 40, "sex": "M", "metrics": METRICS}
        self.assertTrue(build_model(base)["evolution"]["baseline"])
        rows = [{"timestamp_utc": f"2026-10-{d:02d}T10:00:00+00:00", "sensor_type": "polar_h10", "duration_minutes": 5, "rmssd": 30 + d, "sdnn": 40 + d, "hr_mean": 70} for d in (1, 8, 15)]
        m = build_model(dict(base, history=rows, measured_at="2026-11-04T10:00:00Z"))
        self.assertFalse(m["evolution"]["baseline"])
        self.assertEqual(m["evolution"]["n"], 4)


class Pdf(unittest.TestCase):
    def test_genera_pdf_valido_sin_recortes(self):
        m = build_model({"patient_id": "P-1", "age": 40, "sex": "F", "metrics": METRICS})
        pdf = build_pdf(m)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreaterEqual(page_count(pdf), 8)
        self.assertEqual(draw.WARNINGS, [])

    def test_metricas_minimas_y_textos_largos(self):
        for payload in [
            {"patient_id": "M", "metrics": {"sensor_type": "vibration_scg", "duration_minutes": 1, "rmssd": 28.5, "hr_mean": 74}},
            {"patient_id": "X" * 200, "age": 68, "comorbidities": "Hipertensión, " * 40, "notes": "n" * 900,
             "metrics": dict(METRICS, hr_mean=104, rmssd=11, rmssd_corr=12, sdnn=24)},
        ]:
            pdf = build_pdf(build_model(payload))
            self.assertTrue(pdf.startswith(b"%PDF"))
            self.assertEqual(draw.WARNINGS, [])


class Acceso(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()
        routes._fails.clear()
        self.body = json.dumps({"patient_id": "P-9", "age": 40, "metrics": METRICS})
        p = mock.patch.object(routes.time, "sleep", lambda s: None)
        p.start(); self.addCleanup(p.stop)

    def post(self, key=None, body=None, **kw):
        h = {"Content-Type": "application/json"}
        if key is not None:
            h["X-Report-Key"] = quote(key, safe="")
        return self.c.post("/api/report", data=self.body if body is None else body, headers=h, **kw)

    def test_deshabilitado_sin_variable(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("REPORT_PASSWORD", None)
            self.assertFalse(self.c.get("/api/report/status").get_json()["enabled"])
            self.assertEqual(self.post("lo-que-sea").status_code, 503)

    def test_exige_contrasena(self):
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "clave-Secreta ñ€1"}):
            self.assertTrue(self.c.get("/api/report/status").get_json()["enabled"])
            self.assertEqual(self.post().status_code, 401)
            self.assertEqual(self.post("incorrecta").status_code, 401)
            r = self.post("clave-Secreta ñ€1")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.mimetype, "application/pdf")
            self.assertTrue(r.data.startswith(b"%PDF"))
            self.assertIn("informe-hrv-P-9-", r.headers["Content-Disposition"])
            self.assertEqual(r.headers["Cache-Control"], "no-store")

    def test_sin_pdf_en_respuesta_de_error(self):
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "abc"}):
            r = self.post("mal")
            self.assertEqual(r.mimetype, "application/json")
            self.assertNotIn(b"%PDF", r.data)

    def test_bloqueo_por_intentos(self):
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "abc"}):
            for _ in range(routes.MAX_FAILS):
                self.assertEqual(self.post("x").status_code, 401)
            self.assertEqual(self.post("x").status_code, 429)
            self.assertEqual(self.post("abc").status_code, 429)   # ni la correcta pasa durante el bloqueo

    def test_validaciones_de_entrada(self):
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "abc"}):
            self.assertEqual(self.post("abc", body="{no es json").status_code, 400)
            self.assertEqual(self.post("abc", body=json.dumps({"patient_id": "x"})).status_code, 400)
            self.assertEqual(self.post("abc", body=json.dumps({"metrics": {"sensor_type": "polar_h10"}})).status_code, 422)
            big = json.dumps({"metrics": METRICS, "pad": "x" * (2 * 1024 * 1024 + 10)})
            self.assertEqual(self.post("abc", body=big).status_code, 413)

    def test_la_contrasena_no_queda_en_el_pdf_ni_en_la_respuesta(self):
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "zzClaveUnica99"}):
            r = self.post("zzClaveUnica99")
            self.assertNotIn(b"zzClaveUnica99", r.data)
            self.assertNotIn("zzClaveUnica99", str(dict(r.headers)))

    def test_funcion_vercel_api_report_sin_colision_de_nombres(self):
        """api/report.py (función de Vercel) no debe taparse con el paquete hba_report, con api/ primero en sys.path."""
        import importlib.util
        sys.path.insert(0, os.path.join(ROOT, "api"))
        spec = importlib.util.spec_from_file_location("vercel_fn_report", os.path.join(ROOT, "api", "report.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        c = mod.app.test_client()
        self.assertIn(c.get("/api/report/status").status_code, (200,))
        with mock.patch.dict(os.environ, {"REPORT_PASSWORD": "abc"}):
            r = c.post("/api/report", data=self.body, headers={"Content-Type": "application/json", "X-Report-Key": "abc"})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.data.startswith(b"%PDF"))

    def test_api_existentes_intactas(self):
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertEqual(self.c.get("/api/history?patient_id=x").status_code, 200)
        self.assertEqual(self.c.post("/api/compute", json={"sensor_type": "x"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()

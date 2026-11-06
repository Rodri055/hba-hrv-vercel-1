"""
HBA-HRV — api/report.py
Entrada de función Vercel (mismo patrón que compute/save/history). La lógica vive en el paquete /report.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))

from flask import Flask
from hba_report.routes import bp

app = Flask(__name__)
app.register_blueprint(bp)

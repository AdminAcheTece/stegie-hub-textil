import os
from flask import Flask

app = Flask(__name__)

@app.get("/")
def home():
    return "<h1>STEGIE no ar ✅</h1>"

from flask import Blueprint, render_template

bp = Blueprint("main", __name__)

@bp.get("/")
def home():
    services = [
        {
            "name": "Ficha Técnica",
            "description": "Cadastro e gestão de fichas técnicas e parâmetros.",
            "href": "/services/ficha-tecnica",
            "state": "locked",  # ok | locked | denied
        },
        {
            "name": "Treinamentos",
            "description": "Conteúdos e trilhas de capacitação.",
            "href": "/services/treinamentos",
            "state": "ok",
        },
        {
            "name": "Auditoria de Processo",
            "description": "Checklists, indicadores e planos de ação.",
            "href": "/services/auditoria",
            "state": "denied",
        },
    ]
    return render_template("home.html", services=services)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

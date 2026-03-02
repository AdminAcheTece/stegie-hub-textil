import os
from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

# Catálogo inicial de serviços (vitrine)
SERVICES = [
    {
        "slug": "ficha-tecnica",
        "name": "Ficha Técnica",
        "description": "Cadastro e gestão de fichas técnicas e parâmetros.",
        "state": "locked",  # ok | locked | denied
        "tag": "Pacote Profissional",
    },
    {
        "slug": "treinamentos",
        "name": "Treinamentos",
        "description": "Conteúdos e trilhas de capacitação.",
        "state": "ok",
        "tag": "Incluso no plano",
    },
    {
        "slug": "auditoria",
        "name": "Auditoria de Processo",
        "description": "Checklists, indicadores e planos de ação.",
        "state": "denied",
        "tag": "Permissão necessária",
    },
]


# HOME (vitrine)
@app.get("/")
def home():
    # só para exibir um rótulo bonito na página
    state_label = {"ok": "Disponível", "locked": "Bloqueado", "denied": "Sem permissão"}

    services = []
    for s in SERVICES:
        s2 = dict(s)
        s2["href"] = url_for("service_page", slug=s["slug"])
        s2["state_label"] = state_label.get(s["state"], "—")
        services.append(s2)

    return render_template("home.html", services=services)


# PÁGINAS BÁSICAS
@app.get("/planos")
def planos():
    return render_template("planos.html")


@app.get("/login")
def login():
    return render_template("login.html")


@app.get("/cadastro")
def cadastro():
    return render_template("cadastro.html")


@app.get("/servicos")
def servicos():
    return render_template("servicos.html", services=SERVICES)


# PÁGINA DE CADA SERVIÇO
@app.get("/servicos/<slug>")
def service_page(slug):
    service = next((s for s in SERVICES if s["slug"] == slug), None)
    if not service:
        return render_template("404.html"), 404

    # por enquanto: só exibir estado e um texto
    return render_template("service.html", service=service)


# ERRO 404 (página não encontrada)
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

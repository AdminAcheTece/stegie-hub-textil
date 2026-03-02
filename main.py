import os
from flask import Flask, render_template, url_for
from jinja2 import TemplateNotFound

# IMPORTANTE:
# Aqui estamos dizendo ao Flask que:
# - Templates estão em "Modelos"
# - Arquivos estáticos estão em "estática"
app = Flask(
    __name__,
    template_folder="Modelos",
    static_folder="estática",
    static_url_path="/static"
)

# Catálogo inicial (vitrine)
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

@app.get("/")
def home():
    state_label = {"ok": "Disponível", "locked": "Bloqueado", "denied": "Sem permissão"}

    services = []
    for s in SERVICES:
        s2 = dict(s)
        s2["href"] = url_for("service_page", slug=s["slug"])
        s2["state_label"] = state_label.get(s["state"], "—")
        services.append(s2)

    return render_template("home.html", services=services)

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

@app.get("/servicos/<slug>")
def service_page(slug):
    service = next((s for s in SERVICES if s["slug"] == slug), None)
    if not service:
        return render_template("404.html"), 404
    return render_template("service.html", service=service)

@app.errorhandler(404)
def not_found(e):
    # À prova de erro: se faltar 404.html, não quebra o site
    try:
        return render_template("404.html"), 404
    except TemplateNotFound:
        return "404 - Página não encontrada", 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)

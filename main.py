import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)
from jinja2 import ChoiceLoader, FileSystemLoader, FunctionLoader


# -----------------------------
# Paths (robustos para Linux/Render)
# -----------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _first_existing_dir(candidates):
    return next((d for d in candidates if os.path.isdir(d)), None)


def _check_file(base_dir: str, rel_path: str):
    full = os.path.join(base_dir, rel_path)
    if os.path.isfile(full):
        try:
            size = os.path.getsize(full)
        except OSError:
            size = None
        return True, full, size
    return False, full, None


# Templates (podem estar em app/templates, templates, Modelos, etc.)
CANDIDATE_TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, "app", "templates"),   # ✅ comum
    os.path.join(BASE_DIR, "app", "Modelos"),     # fallback
    os.path.join(BASE_DIR, "templates"),          # fallback
    os.path.join(BASE_DIR, "Modelos"),            # fallback
]
TEMPLATE_DIRS = [d for d in CANDIDATE_TEMPLATE_DIRS if os.path.isdir(d)]

# Estáticos (podem estar em app/estática, estática, app/static, static, etc.)
CANDIDATE_STATIC_DIRS = [
    # dentro de app/ (muito comum)
    os.path.join(BASE_DIR, "app", "estática"),
    os.path.join(BASE_DIR, "app", "estatica"),
    os.path.join(BASE_DIR, "app", "static"),
    # na raiz
    os.path.join(BASE_DIR, "estática"),
    os.path.join(BASE_DIR, "estatica"),
    os.path.join(BASE_DIR, "static"),
]
STATIC_DIR = _first_existing_dir(CANDIDATE_STATIC_DIRS)

if not TEMPLATE_DIRS:
    raise RuntimeError(
        "Nenhum diretório de templates encontrado. Verifique se existe 'app/templates', "
        "'templates', 'app/Modelos' ou 'Modelos' no projeto."
    )

if STATIC_DIR is None:
    raise RuntimeError(
        "Nenhum diretório de arquivos estáticos encontrado. Verifique se existe 'app/estática/', "
        "'estática/' (com acento), 'estatica/' ou 'static/' no projeto."
    )


# -----------------------------
# Flask app (ESTÁVEL para Render)
# -----------------------------
# Usa o static nativo do Flask apontando para a pasta real encontrada (STATIC_DIR)
# e template_folder apontando para o primeiro diretório válido (TEMPLATE_DIRS[0]).
app = Flask(
    __name__,
    template_folder=TEMPLATE_DIRS[0],
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# Bust de cache (opcional; usado no base.html via config.get('ASSET_VERSION'))
app.config["ASSET_VERSION"] = os.environ.get("ASSET_VERSION", "1")

# Logs de boot (ajudam MUITO a fechar diagnóstico no Render)
print(f"[BOOT] BASE_DIR={BASE_DIR}")
print(f"[BOOT] TEMPLATE_DIRS={TEMPLATE_DIRS}")
print(f"[BOOT] STATIC_DIR={STATIC_DIR}")

# Verificação objetiva: existe CSS/JS onde o site espera?
for rel in ("css/style.css", "CSS/style.css", "js/app.js", "JS/app.js"):
    ok, full, size = _check_file(STATIC_DIR, rel)
    if ok:
        print(f"[BOOT] STATIC OK: {rel} -> {full} ({size} bytes)")
    else:
        print(f"[BOOT] STATIC MISSING: {rel} (esperado em: {full})")


# -----------------------------
# Jinja loaders (fallback + “parciais opcionais”)
# -----------------------------
def optional_partials_loader(name: str):
    # Se faltar qualquer template dentro de Parciais/, não derruba o site.
    if name.startswith("Parciais/") or name.startswith("parciais/"):
        return ""
    return None


# Ordem importa: procura primeiro nos TEMPLATE_DIRS (na ordem), depois aplica loader opcional
app.jinja_loader = ChoiceLoader([
    FileSystemLoader(TEMPLATE_DIRS),
    FunctionLoader(optional_partials_loader),
])


# -----------------------------
# Conteúdo (mock)
# -----------------------------
ARTIGOS = [
    {
        "slug": "tolerancias-em-malharia",
        "tag": "Qualidade",
        "title": "Tolerâncias em malharia: como definir sem travar produtividade",
        "excerpt": "Como construir tolerâncias praticáveis, conectadas a decisão e rotina — sem engessar o processo.",
        "reading_time": "6 min",
        "date": "2026-03-03",
        "subtitle": "Critérios claros, tolerâncias aplicáveis e a lógica certa para reduzir variação com previsibilidade.",
        "sections": [
            {"h": "O erro mais comum", "p": "Tolerância não é “punição”. É faixa de controle para decisão rápida e repetível."},
            {"h": "Como definir sem travar", "p": "Comece pelo objetivo do produto, identifique variáveis críticas e estabeleça faixas realistas por lote."},
            {"h": "Checklist prático", "p": "Defina: o que medir, quando medir, como registrar e qual ação tomar quando sair do padrão."},
        ],
    },
    {
        "slug": "largura-gramatura-e-variacao",
        "tag": "Processo",
        "title": "Largura, gramatura e variação: onde o sistema realmente abre",
        "excerpt": "Os pontos que mais geram variação e como fechar o sistema com padrão, ficha e rotina.",
        "reading_time": "7 min",
        "date": "2026-03-03",
        "subtitle": "Se você mede mas não decide, você não controla. Vamos fechar o ciclo.",
        "sections": [
            {"h": "Onde abre", "p": "Variação nasce em variáveis críticas sem rotina de checagem e sem critério de ação."},
            {"h": "Como fechar", "p": "Ficha técnica + teste certo + rotina = previsibilidade de decisão e repetição do que funciona."},
        ],
    },
    {
        "slug": "testes-de-qualidade-da-malha",
        "tag": "Testes",
        "title": "Testes de malha: quais usar, quando usar, e como interpretar",
        "excerpt": "Teste bom é o que orienta decisão. O resto vira custo e ruído.",
        "reading_time": "8 min",
        "date": "2026-03-03",
        "subtitle": "Quais testes importam por objetivo e como transformar resultado em ação.",
        "sections": [
            {"h": "Teste certo, hora certa", "p": "Escolha testes por objetivo de produto e risco real do processo."},
            {"h": "Interpretação", "p": "Resultado sem critério de aceite não decide nada. Critério vem antes do teste."},
        ],
    },
]

CASES = [
    {
        "slug": "padronizacao-ficha-e-rotina",
        "title": "Padronização com ficha técnica e rotina",
        "excerpt": "Critérios claros + ficha aplicável + checagens: previsibilidade e menos retrabalho.",
        "sections": [
            {"h": "Desafio", "p": "Oscilação de qualidade e decisões inconsistentes entre áreas."},
            {"h": "Diagnóstico", "p": "Variáveis críticas sem padrão e ausência de critério de aceite."},
            {"h": "Intervenção", "p": "Ficha técnica aplicável, critérios de teste e rotina de verificação."},
            {"h": "Sustentação", "p": "Rituais e auditoria do padrão, ajustes finos e disciplina de registro."},
            {"h": "Resultado", "p": "Processo mais previsível, menos ruído técnico e decisão mais rápida."},
        ],
    }
]


# -----------------------------
# Rotas
# -----------------------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/quem-somos")
def quem_somos():
    return render_template("quem-somos.html")


@app.route("/servicos")
def servicos():
    return render_template("servicos.html")


@app.route("/educacao")
def educacao():
    return render_template("educacao.html")


@app.route("/fichas-tecnicas")
def fichas_tecnicas():
    return render_template("fichas-tecnicas.html")


@app.route("/conteudos")
def conteudos():
    tag = request.args.get("tag")
    artigos = [a for a in ARTIGOS if (not tag or a["tag"] == tag)]
    return render_template("conteudos.html", artigos=artigos, tag=tag)


@app.route("/conteudos/<slug>")
def artigo(slug):
    art = next((a for a in ARTIGOS if a["slug"] == slug), None)
    if not art:
        abort(404)
    more = [a for a in ARTIGOS if a["slug"] != slug][:3]
    return render_template("artigo.html", art=art, more=more)


@app.route("/cases")
def cases():
    return render_template("cases.html", cases=CASES)


@app.route("/cases/<slug>")
def case(slug):
    c = next((x for x in CASES if x["slug"] == slug), None)
    if not c:
        abort(404)
    more = [x for x in CASES if x["slug"] != slug][:3]
    return render_template("case.html", case=c, more=more)


@app.route("/contato", methods=["GET", "POST"])
def contato():
    if request.method == "POST":
        flash("Recebido. Vou analisar seu contexto e retorno com os próximos passos.", "success")
        return redirect(url_for("contato"))

    assunto = request.args.get("assunto", "")
    curso = request.args.get("curso", "")
    return render_template("contato.html", assunto=assunto, curso=curso)


@app.route("/politica-de-privacidade")
def politica():
    return render_template("politica-de-privacidade.html")


@app.route("/termos")
def termos():
    return render_template("termos.html")


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.route("/health")
def health():
    return "ok", 200


# -----------------------------
# Local run (somente dev)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=True)

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
    os.path.join(BASE_DIR, "app", "templates"),
    os.path.join(BASE_DIR, "app", "Modelos"),
    os.path.join(BASE_DIR, "templates"),
    os.path.join(BASE_DIR, "Modelos"),
]
TEMPLATE_DIRS = [d for d in CANDIDATE_TEMPLATE_DIRS if os.path.isdir(d)]

# Estáticos (podem estar em app/static, static, app/estática, estática, etc.)
CANDIDATE_STATIC_DIRS = [
    os.path.join(BASE_DIR, "app", "static"),
    os.path.join(BASE_DIR, "app", "estática"),
    os.path.join(BASE_DIR, "app", "estatica"),
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "estática"),
    os.path.join(BASE_DIR, "estatica"),
]
STATIC_DIR = _first_existing_dir(CANDIDATE_STATIC_DIRS)

if not TEMPLATE_DIRS:
    raise RuntimeError(
        "Nenhum diretório de templates encontrado. Verifique se existe 'app/templates', "
        "'templates', 'app/Modelos' ou 'Modelos' no projeto."
    )

if STATIC_DIR is None:
    raise RuntimeError(
        "Nenhum diretório de arquivos estáticos encontrado. Verifique se existe 'app/static', "
        "'static', 'app/estática', 'estática' (com acento) ou 'estatica'."
    )


# -----------------------------
# Flask app (ESTÁVEL para Render)
# -----------------------------
app = Flask(
    __name__,
    template_folder=TEMPLATE_DIRS[0],
    static_folder=STATIC_DIR,
    static_url_path="/static",
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# Bust de cache (usado no base.html via config.get('ASSET_VERSION'))
app.config["ASSET_VERSION"] = os.environ.get("ASSET_VERSION", "1")

# Logs de boot
print(f"[BOOT] BASE_DIR={BASE_DIR}")
print(f"[BOOT] TEMPLATE_DIRS={TEMPLATE_DIRS}")
print(f"[BOOT] STATIC_DIR={STATIC_DIR}")

# Checagem de arquivos estáticos essenciais
for rel in ("css/stegie.css", "css/style.css", "js/app.js"):
    ok, full, size = _check_file(STATIC_DIR, rel)
    if ok:
        print(f"[BOOT] STATIC OK: {rel} -> {full} ({size} bytes)")
    else:
        print(f"[BOOT] STATIC MISSING: {rel} (esperado em: {full})")


# -----------------------------
# Jinja loaders (fallback + “parciais opcionais”)
# -----------------------------
def optional_partials_loader(name: str):
    if name.startswith("Parciais/") or name.startswith("parciais/"):
        return ""
    return None


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
        "excerpt": "Como construir tolerâncias praticáveis, conectadas a decisão — sem engessar o processo.",
        "reading_time": "6 min",
        "date": "2026-03-03",
        "subtitle": "Critérios claros e tolerâncias aplicáveis para reduzir variação com previsibilidade.",
        "sections": [
            {"h": "O erro mais comum", "p": "Tolerância não é punição. É faixa de controle para decisão rápida."},
            {"h": "Como definir sem travar", "p": "Comece pelo objetivo do produto e feche variáveis críticas por lote."},
            {"h": "Checklist prático", "p": "Defina: o que medir, quando medir, como registrar e qual ação tomar."},
        ],
    },
    {
        "slug": "largura-gramatura-e-variacao",
        "tag": "Processo",
        "title": "Largura, gramatura e variação: onde o sistema realmente abre",
        "excerpt": "Os pontos que mais geram variação e como fechar o sistema com padrão, ficha e rotina.",
        "reading_time": "7 min",
        "date": "2026-03-03",
        "subtitle": "Se você mede mas não decide, você não controla.",
        "sections": [
            {"h": "Onde abre", "p": "Variáveis críticas sem rotina de checagem e sem critério de ação."},
            {"h": "Como fechar", "p": "Ficha + teste certo + rotina = previsibilidade e repetição do que funciona."},
        ],
    },
    {
        "slug": "testes-de-qualidade-da-malha",
        "tag": "Testes",
        "title": "Testes de malha: quais usar, quando usar, e como interpretar",
        "excerpt": "Teste bom é o que orienta decisão. O resto vira custo e ruído.",
        "reading_time": "8 min",
        "date": "2026-03-03",
        "subtitle": "Transforme resultado em decisão com critério antes do teste.",
        "sections": [
            {"h": "Teste certo, hora certa", "p": "Escolha testes por objetivo e risco real do processo."},
            {"h": "Interpretação", "p": "Resultado sem critério de aceite não decide nada."},
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
            {"h": "Resultado", "p": "Processo previsível, menos ruído técnico e decisão mais rápida."},
        ],
    }
]

QUALITY_SHELVES = [
    {
        "id": "instituicoes",
        "title": "Instituições e Entidades",
        "subtitle": "Fontes com base técnica, métodos, estudos, atualização setorial e referência estruturada.",
        "cards": [
            {
                "name": "Inmetro",
                "badge": "Referência oficial",
                "description": "Órgão de referência em metrologia, acreditação, conformidade e conteúdos técnicos para suporte à qualidade.",
                "url": "https://www.gov.br/inmetro/pt-br",
                "image": "/static/img/conteudos/qualidade/inmetro.jpg",
                "cover_title": "Qualidade Oficial",
            },
            {
                "name": "Instituição 02",
                "badge": "Entidade",
                "description": "Atualização setorial, visão técnica e materiais de apoio para profissionais da área.",
                "url": "#",
                "image": "",
                "cover_title": "Métodos",
            },
            {
                "name": "Instituição 03",
                "badge": "Associação",
                "description": "Base de consulta para quem precisa acompanhar boas práticas e evolução da área.",
                "url": "#",
                "image": "",
                "cover_title": "Estudos",
            },
            {
                "name": "Instituição 04",
                "badge": "Centro técnico",
                "description": "Conteúdos aplicados, referências e iniciativas ligadas ao controle e à melhoria contínua.",
                "url": "#",
                "image": "",
                "cover_title": "Qualidade",
            },
        ],
    },
    {
        "id": "laboratorios",
        "title": "Empresas e Laboratórios",
        "subtitle": "Aplicação prática, ensaios, equipamentos, soluções e conhecimento ligado ao campo real.",
        "cards": [
            {
                "name": "Laboratório 01",
                "badge": "Laboratório",
                "description": "Ensaios, suporte técnico e leitura aplicada de resultados para decisões com mais critério.",
                "url": "#",
                "image": "",
                "cover_title": "Ensaios",
            },
            {
                "name": "Empresa 01",
                "badge": "Fornecedor técnico",
                "description": "Soluções e conteúdos que ajudam a entender performance, padrão e estabilidade de produto.",
                "url": "#",
                "image": "",
                "cover_title": "Padrão",
            },
            {
                "name": "Empresa 02",
                "badge": "Tecnologia",
                "description": "Conhecimento aplicado a monitoramento, equipamentos e controle de variáveis.",
                "url": "#",
                "image": "",
                "cover_title": "Controle",
            },
            {
                "name": "Laboratório 02",
                "badge": "Teste",
                "description": "Avaliações físicas, interpretação de resultados e apoio à tomada de decisão.",
                "url": "#",
                "image": "",
                "cover_title": "Teste",
            },
        ],
    },
    {
        "id": "canais",
        "title": "Canais e Vídeos",
        "subtitle": "Conteúdo visual para acompanhar demonstrações, interpretações e aplicações práticas.",
        "cards": [
            {
                "name": "Canal 01",
                "badge": "YouTube",
                "description": "Vídeos, explicações e demonstrações úteis para aprofundar a leitura técnica da qualidade.",
                "url": "#",
                "image": "",
                "cover_title": "Vídeos",
            },
            {
                "name": "Canal 02",
                "badge": "Canal técnico",
                "description": "Explicações práticas sobre defeitos, critérios, testes e acompanhamento de processo.",
                "url": "#",
                "image": "",
                "cover_title": "Defeitos",
            },
            {
                "name": "Canal 03",
                "badge": "Conteúdo visual",
                "description": "Material útil para revisar fundamentos, enxergar aplicações e ampliar repertório.",
                "url": "#",
                "image": "",
                "cover_title": "Inspeção",
            },
            {
                "name": "Canal 04",
                "badge": "Vídeo técnico",
                "description": "Referência para quem aprende melhor com imagem, demonstração e explicação objetiva.",
                "url": "#",
                "image": "",
                "cover_title": "Análise",
            },
        ],
    },
    {
        "id": "redes",
        "title": "Redes Profissionais",
        "subtitle": "Perfis e iniciativas para acompanhar conteúdos curtos, insights e atualização constante.",
        "cards": [
            {
                "name": "Perfil 01",
                "badge": "Instagram",
                "description": "Publicações rápidas com abordagem técnica, prática e educacional sobre qualidade.",
                "url": "#",
                "image": "",
                "cover_title": "Social",
            },
            {
                "name": "Perfil 02",
                "badge": "LinkedIn",
                "description": "Visões mais estratégicas sobre qualidade, gestão, tecnologia e evolução industrial.",
                "url": "#",
                "image": "",
                "cover_title": "Gestão",
            },
            {
                "name": "Perfil 03",
                "badge": "Profissional",
                "description": "Referência para acompanhar percepções de campo, experiências e boas práticas.",
                "url": "#",
                "image": "",
                "cover_title": "Campo",
            },
            {
                "name": "Perfil 04",
                "badge": "Comunidade",
                "description": "Atualização recorrente para manter contato com discussões e movimentos do setor.",
                "url": "#",
                "image": "",
                "cover_title": "Insights",
            },
        ],
    },
    {
        "id": "leituras",
        "title": "Portais e Leituras",
        "subtitle": "Artigos, portais e páginas de aprofundamento para interpretar melhor o tema.",
        "cards": [
            {
                "name": "Portal 01",
                "badge": "Portal",
                "description": "Leituras para ampliar repertório e acompanhar discussões ligadas à qualidade têxtil.",
                "url": "#",
                "image": "",
                "cover_title": "Leituras",
            },
            {
                "name": "Blog 01",
                "badge": "Blog",
                "description": "Conteúdos editoriais com abordagem prática e técnica para estudo contínuo.",
                "url": "#",
                "image": "",
                "cover_title": "Artigos",
            },
            {
                "name": "Biblioteca 01",
                "badge": "Conteúdo",
                "description": "Materiais úteis para consulta e aprofundamento em fundamentos e aplicações.",
                "url": "#",
                "image": "",
                "cover_title": "Consulta",
            },
            {
                "name": "Portal 02",
                "badge": "Atualização",
                "description": "Referência para quem deseja acompanhar tendências, leituras e movimento do tema.",
                "url": "#",
                "image": "",
                "cover_title": "Tendências",
            },
        ],
    },
]


# -----------------------------
# Rotas principais
# -----------------------------
@app.route("/", endpoint="home")
def home_page():
    shortcuts = [
        {"label": "Serviços", "href": url_for("servicos"), "icon": "i-wrench"},
        {"label": "Educação", "href": url_for("educacao"), "icon": "i-grad"},
        {"label": "Fichas técnicas", "href": url_for("fichas_tecnicas"), "icon": "i-file"},
        {"label": "Conteúdos", "href": url_for("conteudos"), "icon": "i-book"},
        {"label": "Cases", "href": url_for("cases"), "icon": "i-briefcase"},
    ]

    nav_links = [
        {"label": "Quem somos", "href": url_for("quem_somos")},
        {"label": "Contato", "href": url_for("contato")},
        {"label": "Política", "href": url_for("politica")},
        {"label": "Termos", "href": url_for("termos")},
    ]

    account = {"href": url_for("home"), "initials": "V"}

    return render_template(
        "home_clean.html",
        shortcuts=shortcuts,
        nav_links=nav_links,
        account=account,
    )


@app.route("/home", endpoint="home_redirect")
def home_redirect():
    return redirect(url_for("home"), code=301)


@app.route("/quem-somos", endpoint="quem_somos")
def quem_somos_page():
    return render_template("quem-somos.html")


@app.route("/o-que-fazemos", endpoint="o_que_fazemos")
def o_que_fazemos_page():
    return render_template("o_que_fazemos.html")


@app.route("/servicos", endpoint="servicos")
def servicos_page():
    return render_template("servicos.html")


@app.route("/solucoes", endpoint="solucoes")
def solucoes_redirect():
    return redirect(url_for("servicos"), code=302)


@app.route("/fichas-tecnicas", endpoint="fichas_tecnicas")
def fichas_tecnicas_page():
    return render_template("fichas-tecnicas.html")


@app.route("/conteudos", endpoint="conteudos")
def conteudos_page():
    tag = request.args.get("tag", "").strip()
    artigos = ARTIGOS if not tag else [
        artigo for artigo in ARTIGOS if artigo["tag"].lower() == tag.lower()
    ]
    return render_template("conteudos.html", artigos=artigos, tag=tag)


@app.route("/conteudos/temas/qualidade", endpoint="conteudos_tema_qualidade")
def conteudos_tema_qualidade():
    return render_template(
        "qualidade.html",
        page_title="Qualidade",
        page_intro="Fontes, canais e referências para acompanhar controle, padronização, ensaios, análise de defeitos e melhoria contínua.",
        shelves=QUALITY_SHELVES,
    )


@app.route("/conteudos/temas/<slug>", endpoint="conteudos_tema_temp")
def conteudos_tema_temp(slug):
    if slug == "qualidade":
        return redirect(url_for("conteudos_tema_qualidade"), code=302)
    return redirect(url_for("conteudos"), code=302)


@app.route("/conteudos/<path:subpath>", endpoint="conteudos_subpagina_temp")
def conteudos_subpagina_temp(subpath):
    return redirect(url_for("conteudos"), code=302)


@app.route("/biblioteca/<path:subpath>", endpoint="biblioteca_subpagina_temp")
def biblioteca_subpagina_temp(subpath):
    return redirect(url_for("conteudos"), code=302)


@app.route("/cases", endpoint="cases")
def cases_page():
    return render_template("cases.html", cases=CASES)


@app.route("/cases/<slug>", endpoint="case")
def case_page(slug):
    c = next((x for x in CASES if x["slug"] == slug), None)
    if not c:
        abort(404)
    more = [x for x in CASES if x["slug"] != slug][:3]
    return render_template("case.html", case=c, more=more)


@app.route("/contato", methods=["GET", "POST"], endpoint="contato")
def contato_page():
    if request.method == "POST":
        flash("Recebido. Vou analisar seu contexto e retorno com os próximos passos.", "success")
        return redirect(url_for("contato"))

    assunto = request.args.get("assunto", "")
    curso = request.args.get("curso", "")
    return render_template("contato.html", assunto=assunto, curso=curso)


@app.route("/politica-de-privacidade", endpoint="politica")
def politica_page():
    return render_template("politica-de-privacidade.html")


@app.route("/termos", endpoint="termos")
def termos_page():
    return render_template("termos.html")


@app.route("/health", endpoint="health")
def health():
    return "ok", 200


# -----------------------------
# Rotas complementares
# -----------------------------
@app.route("/desenvolvimento-de-malhas", endpoint="desenvolvimento_de_malhas_hifen")
@app.route("/desenvolvimento_malhas", endpoint="desenvolvimento_malhas")
def desenvolvimento_malhas():
    return render_template("desenvolvimento_malhas.html")


@app.route("/consultoria-textil", endpoint="consultoria_textil")
def consultoria_textil():
    return render_template("consultoria_textil.html")


@app.route("/educacao", endpoint="educacao")
def educacao():
    return render_template("educacao.html")


@app.route("/agente-tecnico-textil-ia", endpoint="agente_tecnico_textil_ia")
def agente_tecnico_textil_ia():
    return render_template("agente_tecnico_textil_ia.html")


@app.route("/agente-tecnico-textil-ia/ferramenta", endpoint="agente_tecnico_textil_ia_ferramenta")
def agente_tecnico_textil_ia_ferramenta():
    return redirect("/contato")


@app.route("/fichas-tecnicas-malharia", endpoint="fichas_tecnicas_malharia")
def fichas_tecnicas_malharia():
    return render_template("fichas_tecnicas_malharia.html")


@app.route("/fichas-tecnicas-malharia/acesso", endpoint="fichas_tecnicas_malharia_acesso")
def fichas_tecnicas_malharia_acesso():
    return redirect("/login")


# -----------------------------
# Error handlers
# -----------------------------
@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


# -----------------------------
# Local run (somente dev)
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=True)

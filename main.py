import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    session,
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
                "badge": "Instituição pública",
                "description": "Referência oficial no Brasil em metrologia, acreditação, regulamentação e avaliação da conformidade.",
                "url": "https://www.gov.br/inmetro/pt-br",
                "image": "/static/img/conteudos/qualidade/inmetro.jpg",
                "cover_title": "Metrologia",
            },
            {
                "name": "ABNT",
                "badge": "Normalização",
                "description": "Fonte central para normas técnicas brasileiras, consulta normativa e estrutura formal de padronização.",
                "url": "https://abnt.org.br/",
                "image": "/static/img/conteudos/qualidade/abnt.png",
                "cover_title": "Normas",
            },
            {
                "name": "AATCC",
                "badge": "Métodos têxteis",
                "description": "Entidade internacional muito reconhecida em métodos e procedimentos de ensaio aplicados a têxteis.",
                "url": "https://www.aatcc.org/",
                "image": "/static/img/conteudos/qualidade/aatcc.png",
                "cover_title": "Métodos",
            },
            {
                "name": "The Textile Institute",
                "badge": "Entidade internacional",
                "description": "Referência global em profissionalismo, conhecimento e publicações para a cadeia têxtil.",
                "url": "https://www.textileinstitute.org/",
                "image": "/static/img/conteudos/qualidade/textile-institute.jpg",
                "cover_title": "Referência",
            },
        ],
    },
    {
        "id": "laboratorios",
        "title": "Empresas e Laboratórios",
        "subtitle": "Aplicação prática, ensaios, equipamentos, soluções e conhecimento ligado ao campo real.",
        "cards": [
            {
                "name": "SGS",
                "badge": "Ensaios e certificação",
                "description": "Grupo global de testes, inspeção e certificação com atuação forte em têxteis e conformidade.",
                "url": "https://www.sgs.com/en/service-groups/textiles-and-clothing",
                "image": "/static/img/conteudos/qualidade/sgs.png",
                "cover_title": "Ensaios",
            },
            {
                "name": "Intertek",
                "badge": "Teste têxtil",
                "description": "Fonte reconhecida para serviços de ensaio têxtil, conformidade e qualidade de produtos.",
                "url": "https://www.intertek.com/textiles-apparel/textile-testing/",
                "image": "/static/img/conteudos/qualidade/intertek.jpg",
                "cover_title": "Controle",
            },
            {
                "name": "Bureau Veritas",
                "badge": "Compliance",
                "description": "Referência internacional em testes, inspeções e soluções de conformidade para softlines e têxteis.",
                "url": "https://www.cps.bureauveritas.com/needs/textile-testing-services-compliance-solutions",
                "image": "/static/img/conteudos/qualidade/bureau-veritas.png",
                "cover_title": "Compliance",
            },
            {
                "name": "Hohenstein",
                "badge": "Laboratório",
                "description": "Instituição reconhecida por testes e certificações baseados em ciência para têxteis e produtos.",
                "url": "https://www.hohenstein.com/en/",
                "image": "/static/img/conteudos/qualidade/hohenstein.png",
                "cover_title": "Laboratório",
            },
        ],
    },
    {
        "id": "canais",
        "title": "Canais e Vídeos",
        "subtitle": "Conteúdo visual para acompanhar demonstrações, interpretações e aplicações práticas.",
        "cards": [
            {
                "name": "TV Inmetro",
                "badge": "YouTube oficial",
                "description": "Canal oficial com conteúdos sobre qualidade, metrologia, conformidade e informação confiável.",
                "url": "https://www.youtube.com/@tvinmetro",
                "image": "/static/img/conteudos/qualidade/tv-inmetro.jpg",
                "cover_title": "Oficial",
            },
            {
                "name": "AATCC no YouTube",
                "badge": "Canal técnico",
                "description": "Conteúdo institucional e técnico voltado à comunidade profissional de ensaios e métodos têxteis.",
                "url": "https://www.youtube.com/@AatccOrg",
                "image": "/static/img/conteudos/qualidade/aatcc-youtube.jpg",
                "cover_title": "Métodos",
            },
            {
                "name": "The Textile Institute no YouTube",
                "badge": "Webinars",
                "description": "Vídeos, palestras e webinars ligados a atualização técnica e desenvolvimento profissional.",
                "url": "https://www.youtube.com/@thetextileinstitute3333",
                "image": "/static/img/conteudos/qualidade/textile-institute-youtube.jpg",
                "cover_title": "Webinars",
            },
            {
                "name": "Intertek no YouTube",
                "badge": "Qualidade aplicada",
                "description": "Canal institucional com conteúdos de qualidade, testes, conformidade e serviços técnicos.",
                "url": "https://www.youtube.com/intertekgroup",
                "image": "/static/img/conteudos/qualidade/intertek-youtube.jpg",
                "cover_title": "Testes",
            },
        ],
    },
    {
        "id": "redes",
        "title": "Redes Profissionais",
        "subtitle": "Perfis e iniciativas para acompanhar conteúdos curtos, insights e atualização constante.",
        "cards": [
            {
                "name": "Inmetro no LinkedIn",
                "badge": "LinkedIn oficial",
                "description": "Perfil útil para acompanhar atualizações institucionais, programas, qualidade e conformidade.",
                "url": "https://www.linkedin.com/company/inmetro",
                "image": "/static/img/conteudos/qualidade/inmetro-linkedin.png",
                "cover_title": "Atualização",
            },
            {
                "name": "ABNT no LinkedIn",
                "badge": "LinkedIn oficial",
                "description": "Canal profissional para acompanhar normas, lançamentos, eventos e discussões ligadas à padronização.",
                "url": "https://br.linkedin.com/company/abnt-associacao-brasileira-de-normas-tecnicas",
                "image": "/static/img/conteudos/qualidade/abnt-linkedin.jpg",
                "cover_title": "Normas",
            },
            {
                "name": "AATCC no LinkedIn",
                "badge": "LinkedIn oficial",
                "description": "Atualização recorrente sobre eventos, métodos, comunidade técnica e assuntos de qualidade têxtil.",
                "url": "https://www.linkedin.com/company/aatcc",
                "image": "/static/img/conteudos/qualidade/aatcc-linkedin.png",
                "cover_title": "Comunidade",
            },
            {
                "name": "The Textile Institute no LinkedIn",
                "badge": "LinkedIn oficial",
                "description": "Boa fonte para acompanhar debates, publicações e movimentações da comunidade têxtil internacional.",
                "url": "https://uk.linkedin.com/company/the-textile-institute",
                "image": "/static/img/conteudos/qualidade/textile-institute-linkedin.jpg",
                "cover_title": "Rede global",
            },
        ],
    },
    {
        "id": "leituras",
        "title": "Portais e Leituras",
        "subtitle": "Artigos, portais e páginas de aprofundamento para interpretar melhor o tema.",
        "cards": [
            {
                "name": "OEKO-TEX Standards",
                "badge": "Segurança têxtil",
                "description": "Base forte para consulta sobre padrões, selos e segurança de produtos têxteis.",
                "url": "https://www.oeko-tex.com/en/our-standards/",
                "image": "/static/img/conteudos/qualidade/oeko-tex.jpg",
                "cover_title": "Padrões",
            },
            {
                "name": "Textile World",
                "badge": "Revista setorial",
                "description": "Publicação tradicional para acompanhar notícias, tecnologia e movimento industrial têxtil.",
                "url": "https://www.textileworld.com/",
                "image": "/static/img/conteudos/qualidade/textile-world.jpg",
                "cover_title": "Indústria",
            },
            {
                "name": "AATCC News",
                "badge": "Atualização técnica",
                "description": "Página institucional de notícias e press releases voltada à comunidade técnica de ensaios têxteis.",
                "url": "https://www.aatcc.org/press-releases/",
                "image": "/static/img/conteudos/qualidade/aatcc-news.png",
                "cover_title": "Notícias",
            },
            {
                "name": "Textile Institute Publications",
                "badge": "Publicações",
                "description": "Portfólio de livros, revistas, journals e materiais técnicos para aprofundamento profissional.",
                "url": "https://www.textileinstitute.org/publications/textiles-magazine/",
                "image": "/static/img/conteudos/qualidade/textile-institute-publications.jpg",
                "cover_title": "Leituras",
            },
        ],
    },
]

FICHAS_CATALOGO = [
    {
        "slug": "meia-malha-algodao-30-1",
        "nome": "Meia Malha Algodão 30/1",
        "categoria": "Meia Malha",
        "resumo": "Base clássica e versátil para camisetas, com leitura objetiva de composição, gramatura e aplicação.",
        "composicao": "100% Algodão",
        "gramatura": "160 g/m²",
        "aplicacao": "Camisetas básicas",
        "preco": "29,90",
    },
    {
        "slug": "ribana-algodao-elastano",
        "nome": "Ribana Algodão com Elastano",
        "categoria": "Ribana",
        "resumo": "Ficha voltada para bases elásticas aplicadas em punhos, golas e peças com maior ajuste ao corpo.",
        "composicao": "96% Algodão / 4% Elastano",
        "gramatura": "220 g/m²",
        "aplicacao": "Golas, punhos e moda casual",
        "preco": "34,90",
    },
    {
        "slug": "piquet-poliester-viscose",
        "nome": "Piquet Poliéster e Viscose",
        "categoria": "Piquet",
        "resumo": "Estrutura indicada para leitura de bases com textura e aplicação em polos e linhas casuais.",
        "composicao": "65% Poliéster / 35% Viscose",
        "gramatura": "185 g/m²",
        "aplicacao": "Polos e camisaria casual",
        "preco": "32,90",
    },
    {
        "slug": "moletom-p-a-peluciado",
        "nome": "Moletom P.A. Peluciado",
        "categoria": "Moletom",
        "resumo": "Ficha com foco em bases de maior corpo e conforto térmico para linhas de inverno e casual.",
        "composicao": "50% Algodão / 50% Poliéster",
        "gramatura": "300 g/m²",
        "aplicacao": "Moletons e jaquetas leves",
        "preco": "39,90",
    },
    {
        "slug": "suedine-algodao-fino",
        "nome": "Suedine Algodão Fino",
        "categoria": "Suedine",
        "resumo": "Base com leitura interessante para moda infantil, underwear e peças com toque mais delicado.",
        "composicao": "100% Algodão",
        "gramatura": "145 g/m²",
        "aplicacao": "Moda infantil e underwear",
        "preco": "27,90",
    },
    {
        "slug": "jacquard-misto-moda",
        "nome": "Jacquard Misto Moda",
        "categoria": "Jacquard",
        "resumo": "Ficha pensada para bases com desenho e valor agregado em linhas diferenciadas de moda.",
        "composicao": "58% Poliéster / 40% Viscose / 2% Elastano",
        "gramatura": "210 g/m²",
        "aplicacao": "Moda diferenciada",
        "preco": "44,90",
    },
]

# -----------------------------
# Rotas principais
# -----------------------------
@app.route("/", endpoint="home")
def home_page():
    conteudos_qualidade = "/conteudos/temas/qualidade#quality-collections"

    shortcuts = [
        {"label": "Home", "href": url_for("servicos"), "icon": "i-home"},
        {"label": "Consultoria", "href": url_for("consultoria_textil"), "icon": "i-consult"},
        {"label": "Cursos", "href": url_for("educacao"), "icon": "i-grad"},
        {"label": "Fichas Técnicas", "href": url_for("fichas_tecnicas_malharia"), "icon": "i-file"},
        {"label": "Conteúdos", "href": conteudos_qualidade, "icon": "i-book"},
        {"label": "Agente Têxtil", "href": url_for("agente_tecnico_textil_ia"), "icon": "i-bot"},
    ]

    # Rodapé + menu sanduíche (mantém como você pediu)
    nav_links = [
        {"label": "Quem somos", "href": url_for("quem_somos")},
        {"label": "Contato", "href": url_for("contato")},
        {"label": "Política", "href": url_for("politica")},
        {"label": "Termos", "href": url_for("termos")},
    ]

    # CTA conta (círculo preto) — se tiver login no futuro, ajusta aqui
    account = {"href": url_for("login"), "initials": "?"}

    # LISTA DE LOGOS (prova social) — você só coloca os arquivos nessa pasta
    # Caminho sugerido: static/img/clientes/cliente-01.png ... cliente-12.png
    clientes = [
        {"src": url_for("static", filename="img/clientes/cliente-01.png"), "alt": "Empresa atendida 01"},
        {"src": url_for("static", filename="img/clientes/cliente-02.png"), "alt": "Empresa atendida 02"},
        {"src": url_for("static", filename="img/clientes/cliente-03.png"), "alt": "Empresa atendida 03"},
        {"src": url_for("static", filename="img/clientes/cliente-04.png"), "alt": "Empresa atendida 04"},
        {"src": url_for("static", filename="img/clientes/cliente-05.png"), "alt": "Empresa atendida 05"},
        {"src": url_for("static", filename="img/clientes/cliente-06.png"), "alt": "Empresa atendida 06"},
        {"src": url_for("static", filename="img/clientes/cliente-07.png"), "alt": "Empresa atendida 07"},
        {"src": url_for("static", filename="img/clientes/cliente-08.png"), "alt": "Empresa atendida 08"},
    ]

    account = {"href": url_for("home"), "initials": "V"}

    return render_template(
        "home_clean.html",
        shortcuts=shortcuts,
        nav_links=nav_links,
        account=account,
        clientes=clientes,
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
    return redirect(url_for("fichas_login"))


@app.route("/fichas-tecnicas-malharia/catalogo", endpoint="fichas_tecnicas_malharia_catalogo")
def fichas_tecnicas_malharia_catalogo():
    return redirect(url_for("fichas_catalogo"))


@app.route("/fichas/login", endpoint="fichas_login")
def fichas_login():
    return render_template("login_fichas.html")


@app.route("/fichas/catalogo", endpoint="fichas_catalogo")
def fichas_catalogo():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()

    fichas = FICHAS_CATALOGO

    if q:
        termo = q.lower()
        fichas = [
            ficha for ficha in fichas
            if termo in ficha["nome"].lower()
            or termo in ficha["categoria"].lower()
            or termo in ficha["resumo"].lower()
            or termo in ficha["composicao"].lower()
            or termo in ficha["aplicacao"].lower()
        ]

    if categoria:
        fichas = [
            ficha for ficha in fichas
            if ficha["categoria"].lower() == categoria.lower()
        ]

    categorias = sorted({f["categoria"] for f in FICHAS_CATALOGO})

    return render_template(
        "catalogo_fichas.html",
        fichas=fichas,
        categorias=categorias,
        q=q,
        categoria=categoria,
    )

@app.route("/fichas/<slug>", endpoint="fichas_detalhe")
def fichas_detalhe(slug):
    ficha = next((f for f in FICHAS_CATALOGO if f["slug"] == slug), None)

    if not ficha:
        abort(404)

    return f"""
    <html lang='pt-br'>
      <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>{ficha["nome"]} | Fichas Técnicas</title>
        <style>
          body{{
            font-family:Arial,sans-serif;
            margin:0;
            background:#f3f1eb;
            color:#121212;
          }}
          .wrap{{
            width:min(900px, calc(100% - 32px));
            margin:40px auto;
          }}
          .box{{
            background:#fff;
            border-radius:24px;
            padding:32px;
            box-shadow:0 10px 30px rgba(0,0,0,.08);
          }}
          .badge{{
            display:inline-block;
            padding:8px 12px;
            border-radius:999px;
            background:#111;
            color:#fff;
            font-size:12px;
            font-weight:700;
            text-transform:uppercase;
            letter-spacing:.05em;
          }}
          h1{{
            margin:16px 0 10px;
            font-size:38px;
            line-height:1.05;
          }}
          p{{
            color:#555;
            line-height:1.7;
          }}
          .meta{{
            display:grid;
            gap:12px;
            margin:24px 0;
          }}
          .meta div{{
            padding:14px 0;
            border-bottom:1px solid #ece7dc;
          }}
          strong{{
            color:#121212;
          }}
          .actions{{
            display:flex;
            gap:12px;
            flex-wrap:wrap;
            margin-top:24px;
          }}
          a{{
            display:inline-flex;
            align-items:center;
            justify-content:center;
            min-height:48px;
            padding:0 18px;
            border-radius:999px;
            text-decoration:none;
            font-weight:700;
          }}
          .primary{{
            background:#8E8420;
            color:#fff;
          }}
          .ghost{{
            background:#fff;
            color:#121212;
            border:1px solid rgba(18,18,18,.12);
          }}
        </style>
      </head>
      <body>
        <div class='wrap'>
          <div class='box'>
            <span class='badge'>{ficha["categoria"]}</span>
            <h1>{ficha["nome"]}</h1>
            <p>{ficha["resumo"]}</p>

            <div class='meta'>
              <div><strong>Composição:</strong> {ficha["composicao"]}</div>
              <div><strong>Gramatura:</strong> {ficha["gramatura"]}</div>
              <div><strong>Aplicação:</strong> {ficha["aplicacao"]}</div>
              <div><strong>Preço:</strong> R$ {ficha["preco"]}</div>
            </div>

            <div class='actions'>
              <a href='/fichas/login' class='primary'>Comprar esta ficha</a>
              <a href='/fichas/catalogo' class='ghost'>Voltar ao catálogo</a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

@app.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Preencha email e senha.", "error")
            return redirect(url_for("login"))

        # MVP: autenticação simples (sem banco ainda)
        session["user_email"] = email
        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"], endpoint="cadastro")
def cadastro():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        if not nome or not email or not password:
            flash("Preencha todos os campos.", "error")
            return redirect(url_for("cadastro"))

        # MVP: cria sessão direto (persistência vem depois)
        session["user_email"] = email
        flash("Conta criada com sucesso. Você já está logado.", "success")
        return redirect(url_for("home"))

    return render_template("cadastro.html")


@app.route("/conta", endpoint="conta")
def conta():
    if not session.get("user_email"):
        return redirect(url_for("login"))
    return render_template("conta.html", user_email=session.get("user_email"))


@app.route("/logout", endpoint="logout")
def logout():
    session.pop("user_email", None)
    flash("Você saiu da sua conta.", "success")
    return redirect(url_for("home"))

@app.route("/pericia-tecnica-textil")
def pericia_tecnica_textil():
    return render_template("pericia_tecnica_textil.html")

@app.route("/solucoes-vitrine")
def solucoes_vitrine():
    return render_template("solucoes_vitrine.html")

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

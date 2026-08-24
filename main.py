import os
import json
import secrets
import requests
import mercadopago

from mercadopago.webhook import (
    WebhookSignatureValidator,
    InvalidWebhookSignatureError,
)

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    session,
    jsonify,
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

# -----------------------------
# Mercado Pago
# -----------------------------

MERCADO_PAGO_ACCESS_TOKEN = os.environ.get(
    "MERCADO_PAGO_ACCESS_TOKEN",
    ""
).strip()

MERCADO_PAGO_WEBHOOK_SECRET = os.environ.get(
    "MERCADO_PAGO_WEBHOOK_SECRET",
    ""
).strip()

def get_mercadopago_sdk():
    if not MERCADO_PAGO_ACCESS_TOKEN:
        raise RuntimeError(
            "MERCADO_PAGO_ACCESS_TOKEN não está configurado no servidor."
        )

    return mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)

# -----------------------------
# Melhor Envio - Sandbox
# -----------------------------

MELHOR_ENVIO_BASE_URL = os.environ.get(
    "MELHOR_ENVIO_BASE_URL",
    "https://sandbox.melhorenvio.com.br"
).rstrip("/")


MELHOR_ENVIO_CLIENT_ID = os.environ.get(
    "MELHOR_ENVIO_CLIENT_ID",
    ""
).strip()


MELHOR_ENVIO_CLIENT_SECRET = os.environ.get(
    "MELHOR_ENVIO_CLIENT_SECRET",
    ""
).strip()


MELHOR_ENVIO_REDIRECT_URI = os.environ.get(
    "MELHOR_ENVIO_REDIRECT_URI",
    ""
).strip()


MELHOR_ENVIO_USER_AGENT = os.environ.get(
    "MELHOR_ENVIO_USER_AGENT",
    ""
).strip()


# Apenas para os testes no Sandbox.
# Antes da produção criaremos armazenamento permanente.
MELHOR_ENVIO_TOKEN_FILE = (
    "/tmp/kehai_melhor_envio_token.json"
)

# Logs de boot
print(f"[BOOT] BASE_DIR={BASE_DIR}")
print(f"[BOOT] TEMPLATE_DIRS={TEMPLATE_DIRS}")
print(f"[BOOT] STATIC_DIR={STATIC_DIR}")

# Checagem de arquivos estáticos essenciais
for rel in ("css/stegie.css", "js/app.js"):
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
        "id": 1,
        "slug": "meia-malha-algodao-30-1",
        "nome": "Meia Malha Algodão 30/1",
        "categoria": "Meia Malha",
        "resumo": "Base clássica e versátil para camisetas...",
        "composicao": "100% Algodão",
        "gramatura": "160 g/m²",
        "aplicacao": "Camisetas básicas",
        "preco": 29.90,
        "arquivo_pdf": "meia-malha-algodao-30-1.pdf",
        "preview": "meia-malha-algodao-30-1-preview.pdf",
        "capa": "img/fichas/capas/meia-malha-algodao-30-1.jpg",
        "ativo": True,
    },
    {
        "id": 2,
        "slug": "ribana-algodao-elastano",
        "nome": "Ribana Algodão com Elastano",
        "categoria": "Ribana",
        "resumo": "Ficha voltada para bases elásticas aplicadas em punhos, golas e peças com maior ajuste ao corpo.",
        "composicao": "96% Algodão / 4% Elastano",
        "gramatura": "220 g/m²",
        "aplicacao": "Golas, punhos e moda casual",
        "preco": 34.90,
        "arquivo_pdf": "ribana-algodao-30-1.pdf",
        "preview": "ribana-algodao-30-1-preview.pdf",
        "capa": "img/fichas/capas/ribana-algodao-30-1.jpg",
        "ativo": True,
    },    
]

def _parse_preco(value):
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace("R$", "").replace(" ", "")

    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return 0.0


def _enriquecer_fichas(catalogo):
    fichas = []
    used_ids = set()

    for idx, ficha in enumerate(catalogo, start=1):
        item = dict(ficha)

        raw_id = item.get("id")
        if isinstance(raw_id, int) and raw_id not in used_ids:
            item["id"] = raw_id
        else:
            while idx in used_ids:
                idx += 1
            item["id"] = idx
        used_ids.add(item["id"])

        item.setdefault("ativo", True)

        slug = item.get("slug", f"ficha-{item['id']}")
        item["slug"] = slug
        item["preco"] = _parse_preco(item.get("preco", 0))

        item.setdefault("capa", f"img/fichas/capas/{slug}.jpg")
        item.setdefault("arquivo_pdf", f"fichas/{slug}.pdf")
        item.setdefault("preview", f"fichas/previews/{slug}-preview.pdf")

        fichas.append(item)

    return fichas


FICHAS_CATALOGO = _enriquecer_fichas(FICHAS_CATALOGO)


def _buscar_ficha_por_slug(slug):
    return next(
        (f for f in FICHAS_CATALOGO if f["slug"] == slug and f.get("ativo", True)),
        None,
    )


def _buscar_ficha_por_id(ficha_id):
    return next(
        (f for f in FICHAS_CATALOGO if f["id"] == ficha_id and f.get("ativo", True)),
        None,
    )


def _obter_ids_carrinho():
    ids = session.get("fichas_cart", [])
    return ids if isinstance(ids, list) else []


def _salvar_ids_carrinho(ids):
    session["fichas_cart"] = ids
    session.modified = True


def _montar_itens_carrinho():
    ids = _obter_ids_carrinho()
    itens = []

    for ficha_id in ids:
        ficha = _buscar_ficha_por_id(ficha_id)
        if ficha:
            itens.append(ficha)

    total = sum(item["preco"] for item in itens)
    return itens, total


# -----------------------------
# Rotas principais
# -----------------------------
@app.route("/", endpoint="home")
def home_page():
    conteudos_qualidade = "/conteudos/temas/qualidade#quality-collections"

    shortcuts = [
        {"label": "Home", "href": url_for("solucoes_vitrine"), "icon": "i-home"},
        {"label": "Consultoria", "href": url_for("consultoria_textil"), "icon": "i-consult"},
        {"label": "Cursos", "href": url_for("educacao"), "icon": "i-grad"},
        {"label": "Fichas Técnicas", "href": url_for("fichas_catalogo"), "icon": "i-file"},
        {"label": "Conteúdos", "href": conteudos_qualidade, "icon": "i-book"},
        {"label": "Agente Têxtil", "href": url_for("agente_tecnico_textil_ia"), "icon": "i-bot"},
        {"label": "Livro KEHAI", "href": url_for("kehai"), "icon": "i-kehai"},
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
    return redirect(url_for("fichas_catalogo"), code=301)

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
    return redirect(url_for("fichas_catalogo"), code=301)


@app.route("/fichas-tecnicas-malharia/acesso", endpoint="fichas_tecnicas_malharia_acesso")
def fichas_tecnicas_malharia_acesso():
    return redirect(url_for("fichas_login"))


@app.route("/fichas-tecnicas-malharia/catalogo", endpoint="fichas_tecnicas_malharia_catalogo")
def fichas_tecnicas_malharia_catalogo():
    return redirect(url_for("fichas_catalogo"))


@app.route("/fichas/login", endpoint="fichas_login")
def fichas_login():
    return redirect(url_for("fichas_catalogo"), code=301)


@app.route("/fichas/catalogo", endpoint="fichas_catalogo")
def fichas_catalogo():
    q = request.args.get("q", "").strip()
    categoria = request.args.get("categoria", "").strip()

    fichas = [f for f in FICHAS_CATALOGO if f.get("ativo", True)]

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

    categorias = sorted({f["categoria"] for f in FICHAS_CATALOGO if f.get("ativo", True)})

    return render_template(
        "fichas/catalogo.html",
        fichas=fichas,
        categorias=categorias,
        q=q,
        categoria=categoria,
    )
@app.route("/fichas/<slug>", endpoint="fichas_detalhe")
def fichas_detalhe(slug):
    ficha = _buscar_ficha_por_slug(slug)

    if not ficha:
        abort(404)

    relacionadas = [
        f for f in FICHAS_CATALOGO
        if f["slug"] != ficha["slug"]
        and f["categoria"] == ficha["categoria"]
        and f.get("ativo", True)
    ][:3]

    return render_template(
        "fichas/detalhe.html",
        ficha=ficha,
        relacionadas=relacionadas,
    )

@app.route("/fichas/carrinho", endpoint="fichas_carrinho")
def fichas_carrinho():
    itens, total = _montar_itens_carrinho()
    return render_template(
        "fichas/carrinho.html",
        itens=itens,
        total=total,
    )

@app.route("/fichas/carrinho/adicionar/<int:ficha_id>", methods=["POST"], endpoint="fichas_adicionar_carrinho")
def fichas_adicionar_carrinho(ficha_id):
    ficha = _buscar_ficha_por_id(ficha_id)

    if not ficha:
        abort(404)

    ids = _obter_ids_carrinho()

    if ficha_id not in ids:
        ids.append(ficha_id)
        _salvar_ids_carrinho(ids)
        flash("Ficha adicionada ao carrinho.", "success")
    else:
        flash("Essa ficha já está no carrinho.", "info")

    return redirect(url_for("fichas_carrinho"))


@app.route("/fichas/carrinho/remover/<int:ficha_id>", methods=["POST"], endpoint="fichas_remover_carrinho")
def fichas_remover_carrinho(ficha_id):
    ids = _obter_ids_carrinho()

    if ficha_id in ids:
        ids.remove(ficha_id)
        _salvar_ids_carrinho(ids)
        flash("Ficha removida do carrinho.", "success")

    return redirect(url_for("fichas_carrinho"))


@app.route("/fichas/comprar/<int:ficha_id>", methods=["POST"], endpoint="fichas_comprar_agora")
def fichas_comprar_agora(ficha_id):
    ficha = _buscar_ficha_por_id(ficha_id)

    if not ficha:
        abort(404)

    _salvar_ids_carrinho([ficha_id])
    flash("Compra direta iniciada. Revise seu carrinho para seguir ao pagamento.", "success")
    return redirect(url_for("fichas_carrinho"))

@app.route("/fichas/checkout", methods=["POST"], endpoint="fichas_checkout")
def fichas_checkout():
    itens, total = _montar_itens_carrinho()
    email = request.form.get("email", "").strip().lower()

    if not itens:
        flash("Seu carrinho está vazio.", "info")
        return redirect(url_for("fichas_catalogo"))

    if not email:
        flash("Informe seu e-mail para continuar a compra.", "info")
        return redirect(url_for("fichas_carrinho"))

    session["checkout_email"] = email
    session.modified = True

    # Etapa provisória:
    # por enquanto apenas validamos os dados e simulamos a continuidade do fluxo.
    # Na próxima etapa, este redirect será trocado pela integração real com o Mercado Pago.
    return redirect(url_for("fichas_checkout_sucesso"))


@app.route("/fichas/checkout/sucesso", endpoint="fichas_checkout_sucesso")
def fichas_checkout_sucesso():
    email = session.get("checkout_email", "")
    itens, total = _montar_itens_carrinho()

    return render_template(
        "fichas/checkout_sucesso.html",
        email=email,
        itens=itens,
        total=total,
    )

@app.route("/fichas/checkout/falha", endpoint="fichas_checkout_falha")
def fichas_checkout_falha():
    return render_template("fichas/checkout_falha.html")

@app.route("/fichas/checkout/pendente", endpoint="fichas_checkout_pendente")
def fichas_checkout_pendente():
    return render_template("fichas/checkout_pendente.html")

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

# ==========================================================
# KEHAI — FILOSOFIA
# ==========================================================

@app.route("/kehai")
def kehai():
    return render_template("kehai.html")

# ==========================================================
# KEHAI — LANDING PAGE DO LIVRO
# ==========================================================

@app.route("/kehai/livro")
def kehai_livro():
    return render_template("kehai_livro.html")

# =====================================================
# KEHAI - MELHOR ENVIO - AUTORIZAÇÃO
# =====================================================

@app.route("/api/kehai/melhor-envio/autorizar")
def kehai_melhor_envio_autorizar():

    if not all([
        MELHOR_ENVIO_CLIENT_ID,
        MELHOR_ENVIO_CLIENT_SECRET,
        MELHOR_ENVIO_REDIRECT_URI,
        MELHOR_ENVIO_USER_AGENT,
    ]):
        return (
            "Configuração do Melhor Envio incompleta.",
            500
        )

    state = secrets.token_urlsafe(24)

    session[
        "melhor_envio_oauth_state"
    ] = state

    params = {
        "client_id": MELHOR_ENVIO_CLIENT_ID,
        "redirect_uri": MELHOR_ENVIO_REDIRECT_URI,
        "response_type": "code",
        "state": state,
        "scope": "shipping-calculate",
    }

    authorization_url = (
        f"{MELHOR_ENVIO_BASE_URL}"
        "/oauth/authorize"
    )

    return redirect(
        authorization_url
        + "?"
        + requests.compat.urlencode(params)
    )

@app.route(
    "/api/kehai/melhor-envio/callback"
)
def kehai_melhor_envio_callback():

    erro = request.args.get("error")

    if erro:
        return (
            f"Autorização negada: {erro}",
            400
        )


    code = request.args.get("code")

    state = request.args.get("state")


    expected_state = session.pop(
        "melhor_envio_oauth_state",
        None
    )


    if (
        not state
        or not expected_state
        or state != expected_state
    ):
        return (
            "Estado de autorização inválido.",
            400
        )


    if not code:
        return (
            "Código de autorização não recebido.",
            400
        )


    token_url = (
        f"{MELHOR_ENVIO_BASE_URL}"
        "/oauth/token"
    )


    payload = {
        "grant_type":
            "authorization_code",

        "client_id":
            MELHOR_ENVIO_CLIENT_ID,

        "client_secret":
            MELHOR_ENVIO_CLIENT_SECRET,

        "redirect_uri":
            MELHOR_ENVIO_REDIRECT_URI,

        "code":
            code,
    }


    headers = {
        "Accept":
            "application/json",

        "User-Agent":
            MELHOR_ENVIO_USER_AGENT,
    }


    response = requests.post(
        token_url,
        data=payload,
        headers=headers,
        timeout=20,
    )


    if not response.ok:

        print(
            "[MELHOR ENVIO] "
            f"Erro OAuth: {response.status_code} "
            f"{response.text}"
        )

        return (
            "Não foi possível concluir "
            "a autorização do Melhor Envio.",
            500
        )


    token_data = response.json()


    # Armazenamento temporário apenas no Sandbox.
    with open(
        MELHOR_ENVIO_TOKEN_FILE,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            token_data,
            arquivo
        )


    print(
        "[MELHOR ENVIO] "
        "Autorização concluída com sucesso."
    )


    return """
    <h1>Melhor Envio autorizado</h1>
    <p>
        A integração KEHAI foi autorizada
        com sucesso no ambiente Sandbox.
    </p>
    """

# =====================================================
# KEHAI - MELHOR ENVIO - COTAÇÃO DE FRETE
# =====================================================

@app.route(
    "/api/kehai/frete",
    methods=["POST"]
)
def kehai_calcular_frete():

    try:

        # ---------------------------------------------
        # 1. Receber o CEP informado pelo comprador
        # ---------------------------------------------

        dados = request.get_json(
            silent=True
        ) or {}


        cep_destino = str(
            dados.get("cep", "")
        )


        cep_destino = (
            cep_destino
            .replace("-", "")
            .replace(".", "")
            .replace(" ", "")
        )


        if (
            len(cep_destino) != 8
            or not cep_destino.isdigit()
        ):

            return jsonify({
                "success": False,
                "error": "CEP inválido."
            }), 400


        # ---------------------------------------------
        # 2. Carregar o token do Melhor Envio
        # ---------------------------------------------

        if not os.path.exists(
            MELHOR_ENVIO_TOKEN_FILE
        ):

            return jsonify({
                "success": False,
                "error":
                    "Melhor Envio ainda não autorizado."
            }), 500


        with open(
            MELHOR_ENVIO_TOKEN_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            token_data = json.load(
                arquivo
            )


        access_token = token_data.get(
            "access_token"
        )


        if not access_token:

            return jsonify({
                "success": False,
                "error":
                    "Token do Melhor Envio não encontrado."
            }), 500


        # ---------------------------------------------
        # 3. Montar a cotação
        # ---------------------------------------------

        payload = {

            "from": {
                "postal_code":
                    "89260215"
            },

            "to": {
                "postal_code":
                    cep_destino
            },

            "products": [
                {
                    "id":
                        "KEHAI-LIVRO-FISICO",

                    "width":
                        18,

                    "height":
                        4,

                    "length":
                        25,

                    "weight":
                        0.25,

                    "insurance_value":
                        79.90,

                    "quantity":
                        1
                }
            ],

            "options": {
                "receipt":
                    False,

                "own_hand":
                    False,

                "collect":
                    False
            }
        }


        # ---------------------------------------------
        # 4. Chamar a API do Melhor Envio
        # ---------------------------------------------

        url = (
            f"{MELHOR_ENVIO_BASE_URL}"
            "/api/v2/me/shipment/calculate"
        )


        headers = {
            "Authorization":
                f"Bearer {access_token}",

            "Accept":
                "application/json",

            "Content-Type":
                "application/json",

            "User-Agent":
                MELHOR_ENVIO_USER_AGENT,
        }


        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=20,
        )


        if not response.ok:

            print(
                "[MELHOR ENVIO] "
                f"Erro cotação: "
                f"{response.status_code} "
                f"{response.text}"
            )

            return jsonify({
                "success": False,
                "error":
                    "Não foi possível calcular o frete."
            }), 500


        cotacoes = response.json()


        # ---------------------------------------------
        # 5. Filtrar somente cotações válidas
        # ---------------------------------------------

        opcoes = []


        for cotacao in cotacoes:

            if cotacao.get("error"):
                continue


            preco = (
                cotacao.get("custom_price")
                or cotacao.get("price")
            )


            prazo = (
                cotacao.get(
                    "custom_delivery_time"
                )
                or cotacao.get(
                    "delivery_time"
                )
            )


            company = (
                cotacao.get("company")
                or {}
            )


            opcoes.append({
                "id":
                    cotacao.get("id"),

                "servico":
                    cotacao.get("name"),

                "transportadora":
                    company.get("name"),

                "preco":
                    preco,

                "prazo_dias":
                    prazo,
            })


        return jsonify({
            "success": True,
            "cep":
                cep_destino,
            "opcoes":
                opcoes
        })


    except Exception as erro:

        print(
            "[MELHOR ENVIO] "
            f"Erro inesperado na cotação: {erro}"
        )

        return jsonify({
            "success": False,
            "error":
                "Erro interno ao calcular o frete."
        }), 500

# =====================================================
# KEHAI - CHECKOUT MERCADO PAGO
# =====================================================

@app.route("/api/kehai/checkout", methods=["POST"])
def kehai_checkout():

    try:
        dados = request.get_json(silent=True) or {}

        produto = dados.get("product")

        produtos_kehai = {
            "physical": {
                "title": "KEHAI - Livro Físico",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": 79.90,
            }
        }

        if produto not in produtos_kehai:
            return jsonify({
                "success": False,
                "error": "Produto inválido."
            }), 400

        sdk = get_mercadopago_sdk()

        preference_data = {

            "items": [
                produtos_kehai[produto]
            ],

            "back_urls": {
                "success": "https://www.stegie.com.br/kehai/compra/sucesso",
                "failure": "https://www.stegie.com.br/kehai/compra/erro",
                "pending": "https://www.stegie.com.br/kehai/compra/pendente",
            },

            "auto_return": "approved",

            "external_reference": f"KEHAI-{produto}",
        }

        preference_response = sdk.preference().create(
            preference_data
        )

        preference = preference_response["response"]

        return jsonify({
            "success": True,
            "preference_id": preference.get("id"),
            "checkout_url": preference.get("init_point"),
            "sandbox_checkout_url": preference.get("sandbox_init_point"),
        })

    except Exception as erro:

        print(
            f"[MERCADO PAGO] Erro ao criar checkout: {erro}"
        )

        return jsonify({
            "success": False,
            "error": "Não foi possível iniciar o pagamento."
        }), 500

# =====================================================
# KEHAI - WEBHOOK MERCADO PAGO
# =====================================================

@app.route("/api/kehai/webhook", methods=["POST"])
def kehai_mercadopago_webhook():

    try:

        # -------------------------------------------------
        # 1. Verificar se a chave secreta está configurada
        # -------------------------------------------------

        if not MERCADO_PAGO_WEBHOOK_SECRET:

            print(
                "[MERCADO PAGO WEBHOOK] "
                "Assinatura secreta não configurada."
            )

            return jsonify({
                "received": False,
                "error": "Webhook não configurado."
            }), 500


        # -------------------------------------------------
        # 2. Validar se a notificação veio do Mercado Pago
        # -------------------------------------------------

        x_signature = request.headers.get(
            "x-signature"
        )

        x_request_id = request.headers.get(
            "x-request-id"
        )

        data_id_query = request.args.get(
            "data.id"
        )


        try:

            WebhookSignatureValidator.validate(
                x_signature,
                x_request_id,
                data_id_query,
                MERCADO_PAGO_WEBHOOK_SECRET,
            )

        except InvalidWebhookSignatureError:

            print(
                "[MERCADO PAGO WEBHOOK] "
                "Assinatura inválida."
            )

            return jsonify({
                "received": False,
                "error": "Assinatura inválida."
            }), 401


        # -------------------------------------------------
        # 3. Ler os dados da notificação
        # -------------------------------------------------

        dados = request.get_json(
            silent=True
        ) or {}


        tipo = (
            dados.get("type")
            or request.args.get("type")
        )


        data_id = (
            dados.get("data", {}).get("id")
            or data_id_query
        )


        print(
            "[MERCADO PAGO WEBHOOK] "
            f"type={tipo} "
            f"data_id={data_id}"
        )


        # -------------------------------------------------
        # 4. Consultar o pagamento no Mercado Pago
        # -------------------------------------------------

        if tipo == "payment" and data_id:

            sdk = get_mercadopago_sdk()

            pagamento_response = (
                sdk.payment().get(
                    data_id
                )
            )


            pagamento = pagamento_response.get(
                "response",
                {}
            )


            status = pagamento.get(
                "status"
            )


            external_reference = pagamento.get(
                "external_reference"
            )


            valor = pagamento.get(
                "transaction_amount"
            )


            print(
                "[MERCADO PAGO WEBHOOK] "
                f"payment_id={data_id} "
                f"status={status} "
                f"external_reference={external_reference} "
                f"valor={valor}"
            )


        # -------------------------------------------------
        # 5. Confirmar recebimento
        # -------------------------------------------------

        return jsonify({
            "received": True
        }), 200


    except Exception as erro:

        print(
            "[MERCADO PAGO WEBHOOK] "
            f"Erro inesperado: {erro}"
        )


        return jsonify({
            "received": False
        }), 500

# =====================================================
# KEHAI - RETORNOS DO PAGAMENTO
# =====================================================

@app.route("/kehai/compra/sucesso")
def kehai_compra_sucesso():
    return """
    <h1>Pagamento aprovado</h1>
    <p>Obrigado pela sua compra do livro KEHAI.</p>
    """


@app.route("/kehai/compra/pendente")
def kehai_compra_pendente():
    return """
    <h1>Pagamento pendente</h1>
    <p>Seu pagamento está sendo processado.</p>
    """


@app.route("/kehai/compra/erro")
def kehai_compra_erro():
    return """
    <h1>Pagamento não concluído</h1>
    <p>Não foi possível concluir o pagamento.</p>
    """

@app.route("/solucoes-vitrine")
def solucoes_vitrine():
    return render_template("solucoes_vitrine.html")

@app.route("/formacao-malharia")
def formacao_malharia():
    return render_template("formacao_malharia.html")

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

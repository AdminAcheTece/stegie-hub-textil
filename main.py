import os
import json
import secrets
import base64
import hashlib
import hmac
import sqlite3
import re
import requests
import mercadopago
import boto3

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

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

# Sessões mais seguras no ambiente publicado.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.environ.get("RENDER"))
app.permanent_session_lifetime = timedelta(hours=8)

# Acesso administrativo do pós-venda KEHAI.
# Configure esta variável no Render e não salve a senha no GitHub.
KEHAI_ADMIN_PASSWORD = os.environ.get(
    "KEHAI_ADMIN_PASSWORD",
    ""
).strip()

# -----------------------------
# E-mails transacionais KEHAI / Brevo
# -----------------------------
# Nunca salve a API Key no GitHub. Configure tudo no Render.
BREVO_API_KEY = os.environ.get(
    "BREVO_API_KEY",
    ""
).strip()

KEHAI_EMAIL_FROM = os.environ.get(
    "KEHAI_EMAIL_FROM",
    ""
).strip()

KEHAI_EMAIL_FROM_NAME = os.environ.get(
    "KEHAI_EMAIL_FROM_NAME",
    "KEHAI"
).strip() or "KEHAI"

KEHAI_EMAIL_REPLY_TO = os.environ.get(
    "KEHAI_EMAIL_REPLY_TO",
    KEHAI_EMAIL_FROM,
).strip()

KEHAI_EMAIL_BASE_URL = "https://api.brevo.com/v3/smtp/email"

KEHAI_PUBLIC_BASE_URL = (
    os.environ.get(
        "KEHAI_PUBLIC_BASE_URL",
        "https://www.stegie.com.br",
    )
    .strip()
    .rstrip("/")
)

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


# O Melhor Envio assina os webhooks com o secret do aplicativo.
# Por padrão usamos o mesmo CLIENT_SECRET já configurado.
# A variável dedicada é opcional, caso queira separar a configuração.
MELHOR_ENVIO_WEBHOOK_SECRET = os.environ.get(
    "MELHOR_ENVIO_WEBHOOK_SECRET",
    MELHOR_ENVIO_CLIENT_SECRET,
).strip()


MELHOR_ENVIO_REDIRECT_URI = os.environ.get(
    "MELHOR_ENVIO_REDIRECT_URI",
    ""
).strip()


MELHOR_ENVIO_USER_AGENT = os.environ.get(
    "MELHOR_ENVIO_USER_AGENT",
    ""
).strip()


# Permissões necessárias para cotação + compra + geração + impressão.
MELHOR_ENVIO_SCOPES = " ".join([
    "shipping-calculate",
    "cart-read",
    "cart-write",
    "shipping-checkout",
    "shipping-generate",
    "shipping-print",
    "shipping-tracking",
    "orders-read",
])


# Dados do remetente comercial.
# Configure no Render; não salve CNPJ/endereço fiscal no GitHub.
MELHOR_ENVIO_FROM_NAME = os.environ.get(
    "MELHOR_ENVIO_FROM_NAME", ""
).strip()

MELHOR_ENVIO_FROM_EMAIL = os.environ.get(
    "MELHOR_ENVIO_FROM_EMAIL", ""
).strip()

MELHOR_ENVIO_FROM_PHONE = os.environ.get(
    "MELHOR_ENVIO_FROM_PHONE", ""
).strip()

MELHOR_ENVIO_FROM_COMPANY_DOCUMENT = os.environ.get(
    "MELHOR_ENVIO_FROM_COMPANY_DOCUMENT", ""
).strip()


MELHOR_ENVIO_FROM_ECONOMIC_ACTIVITY_CODE = os.environ.get(
    "MELHOR_ENVIO_FROM_ECONOMIC_ACTIVITY_CODE", ""
).strip()

MELHOR_ENVIO_FROM_ADDRESS = os.environ.get(
    "MELHOR_ENVIO_FROM_ADDRESS", ""
).strip()

MELHOR_ENVIO_FROM_NUMBER = os.environ.get(
    "MELHOR_ENVIO_FROM_NUMBER", ""
).strip()

MELHOR_ENVIO_FROM_COMPLEMENT = os.environ.get(
    "MELHOR_ENVIO_FROM_COMPLEMENT", ""
).strip()

MELHOR_ENVIO_FROM_DISTRICT = os.environ.get(
    "MELHOR_ENVIO_FROM_DISTRICT", ""
).strip()

MELHOR_ENVIO_FROM_CITY = os.environ.get(
    "MELHOR_ENVIO_FROM_CITY", ""
).strip()

MELHOR_ENVIO_FROM_POSTAL_CODE = os.environ.get(
    "MELHOR_ENVIO_FROM_POSTAL_CODE",
    "89260215"
).strip()

MELHOR_ENVIO_FROM_STATE_ABBR = os.environ.get(
    "MELHOR_ENVIO_FROM_STATE_ABBR", ""
).strip().upper()


# Token OAuth persistente no disco do Render.
MELHOR_ENVIO_TOKEN_FILE = (
    "/var/data/kehai_melhor_envio_token.json"
)

# -----------------------------
# Melhor Envio - Gerenciamento de Token
# -----------------------------

def carregar_token_melhor_envio():

    if not os.path.exists(
        MELHOR_ENVIO_TOKEN_FILE
    ):
        return None


    try:

        with open(
            MELHOR_ENVIO_TOKEN_FILE,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(
                arquivo
            )

    except Exception as erro:

        print(
            "[MELHOR ENVIO] "
            f"Erro ao carregar token: {erro}"
        )

        return None


def salvar_token_melhor_envio(
    token_data
):

    pasta = os.path.dirname(
        MELHOR_ENVIO_TOKEN_FILE
    )


    os.makedirs(
        pasta,
        exist_ok=True
    )


    arquivo_temporario = (
        MELHOR_ENVIO_TOKEN_FILE
        + ".tmp"
    )


    with open(
        arquivo_temporario,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            token_data,
            arquivo
        )


    os.replace(
        arquivo_temporario,
        MELHOR_ENVIO_TOKEN_FILE
    )


def renovar_token_melhor_envio():

    token_atual = (
        carregar_token_melhor_envio()
    )


    if not token_atual:

        raise RuntimeError(
            "Token do Melhor Envio não encontrado."
        )


    refresh_token = token_atual.get(
        "refresh_token"
    )


    if not refresh_token:

        raise RuntimeError(
            "Refresh token do Melhor Envio não encontrado."
        )


    token_url = (
        f"{MELHOR_ENVIO_BASE_URL}"
        "/oauth/token"
    )


    payload = {

        "grant_type":
            "refresh_token",

        "client_id":
            MELHOR_ENVIO_CLIENT_ID,

        "client_secret":
            MELHOR_ENVIO_CLIENT_SECRET,

        "refresh_token":
            refresh_token,
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
            "Falha ao renovar token. "
            f"HTTP {response.status_code}"
        )

        raise RuntimeError(
            "Não foi possível renovar "
            "o token do Melhor Envio."
        )


    novo_token = response.json()


    salvar_token_melhor_envio(
        novo_token
    )


    print(
        "[MELHOR ENVIO] "
        "Token renovado com sucesso."
    )


    return novo_token


def somente_digitos(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def validar_chave_nfe_modelo_55(chave):
    """
    Valida a estrutura básica da chave de acesso de uma NF-e modelo 55.

    Regras verificadas:
    - exatamente 44 dígitos;
    - modelo do documento fiscal = 55;
    - dígito verificador (módulo 11) correto;
    - em produção, o CNPJ embutido na chave deve coincidir com o
      CNPJ do remetente configurado no Render.

    No Sandbox do Melhor Envio, a conferência de correspondência do
    CNPJ é propositalmente dispensada para permitir chaves fictícias
    estruturais de teste. Em produção, essa conferência é obrigatória.
    """
    chave = somente_digitos(chave)

    if len(chave) != 44:
        return False, "A chave da NF-e deve conter exatamente 44 dígitos."

    # Estrutura da chave:
    # cUF(2) + AAMM(4) + CNPJ(14) + modelo(2) + série(3) +
    # nNF(9) + tpEmis(1) + cNF(8) + cDV(1)
    modelo = chave[20:22]
    if modelo != "55":
        return False, (
            "A chave informada não é de uma NF-e modelo 55. "
            f"Modelo encontrado na chave: {modelo or '—'}."
        )

    base = chave[:43]
    dv_informado = int(chave[43])

    peso = 2
    soma = 0
    for caractere in reversed(base):
        soma += int(caractere) * peso
        peso += 1
        if peso > 9:
            peso = 2

    resto = soma % 11
    dv_calculado = 0 if resto in (0, 1) else 11 - resto

    if dv_informado != dv_calculado:
        return False, (
            "A chave da NF-e possui dígito verificador inválido. "
            "Revise a chave antes de continuar."
        )

    # Fora do Sandbox, garante que a nota pertence à mesma empresa
    # configurada como remetente da operação KEHAI.
    if "sandbox" not in MELHOR_ENVIO_BASE_URL.lower():
        cnpj_remetente = somente_digitos(MELHOR_ENVIO_FROM_COMPANY_DOCUMENT)
        cnpj_na_chave = chave[6:20]

        if len(cnpj_remetente) == 14 and cnpj_na_chave != cnpj_remetente:
            return False, (
                "O CNPJ existente na chave da NF-e não corresponde "
                "ao CNPJ do remetente configurado no Render."
            )

    return True, None


def melhor_envio_request(method, endpoint, *, json_payload=None, timeout=30):
    """
    Executa chamada autenticada ao Melhor Envio e tenta renovar
    o access_token uma vez em caso de 401.
    """
    token_data = carregar_token_melhor_envio()
    if not token_data or not token_data.get("access_token"):
        raise RuntimeError("Melhor Envio ainda não autorizado.")

    url = f"{MELHOR_ENVIO_BASE_URL}{endpoint}"

    def _headers(access_token):
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": MELHOR_ENVIO_USER_AGENT,
        }

    access_token = token_data["access_token"]
    response = requests.request(
        method.upper(),
        url,
        json=json_payload,
        headers=_headers(access_token),
        timeout=timeout,
    )

    if response.status_code == 401:
        novo_token = renovar_token_melhor_envio()
        access_token = novo_token.get("access_token")
        if not access_token:
            raise RuntimeError("Novo access token não recebido.")

        response = requests.request(
            method.upper(),
            url,
            json=json_payload,
            headers=_headers(access_token),
            timeout=timeout,
        )

    return response


def validar_configuracao_remetente_melhor_envio():
    campos = {
        "MELHOR_ENVIO_FROM_NAME": MELHOR_ENVIO_FROM_NAME,
        "MELHOR_ENVIO_FROM_EMAIL": MELHOR_ENVIO_FROM_EMAIL,
        "MELHOR_ENVIO_FROM_PHONE": MELHOR_ENVIO_FROM_PHONE,
        "MELHOR_ENVIO_FROM_COMPANY_DOCUMENT": MELHOR_ENVIO_FROM_COMPANY_DOCUMENT,
        "MELHOR_ENVIO_FROM_ADDRESS": MELHOR_ENVIO_FROM_ADDRESS,
        "MELHOR_ENVIO_FROM_NUMBER": MELHOR_ENVIO_FROM_NUMBER,
        "MELHOR_ENVIO_FROM_DISTRICT": MELHOR_ENVIO_FROM_DISTRICT,
        "MELHOR_ENVIO_FROM_CITY": MELHOR_ENVIO_FROM_CITY,
        "MELHOR_ENVIO_FROM_POSTAL_CODE": MELHOR_ENVIO_FROM_POSTAL_CODE,
        "MELHOR_ENVIO_FROM_STATE_ABBR": MELHOR_ENVIO_FROM_STATE_ABBR,
    }
    missing = [key for key, value in campos.items() if not str(value or "").strip()]
    if missing:
        raise RuntimeError(
            "Configuração fiscal/remetente incompleta no Render: "
            + ", ".join(missing)
        )


# -----------------------------
# KEHAI - Pedidos e persistência
# -----------------------------

KEHAI_DATA_DIR = os.environ.get(
    "KEHAI_DATA_DIR",
    "/var/data"
).strip() or "/var/data"

KEHAI_DB_PATH = os.path.join(
    KEHAI_DATA_DIR,
    "kehai.sqlite3"
)

KEHAI_ORIGIN_POSTAL_CODE = "89260215"

KEHAI_PRODUCTS = {
    "physical": {
        "code": "KEHAI-LIVRO-FISICO",
        "title": "KEHAI - Livro Físico",
        "quantity": 1,
        "unit_price_cents": 7990,
        "weight": 0.25,
        "length": 25,
        "width": 18,
        "height": 4,
    }
}

# =====================================================
# KEHAI EBOOK - CLOUDFLARE R2
# =====================================================

# Link real do R2:
# válido por 10 minutos.
KEHAI_R2_URL_EXPIRES_SECONDS = 600


# Cada compra poderá solicitar
# até 10 downloads.
KEHAI_EBOOK_DOWNLOAD_LIMIT = 10

def get_kehai_r2_config():

    config = {

        "access_key_id":
            os.environ.get(
                "R2_ACCESS_KEY_ID",
                ""
            ).strip(),

        "secret_access_key":
            os.environ.get(
                "R2_SECRET_ACCESS_KEY",
                ""
            ).strip(),

        "endpoint_url":
            os.environ.get(
                "R2_ENDPOINT_URL",
                ""
            ).strip(),

        "bucket_name":
            os.environ.get(
                "R2_BUCKET_NAME",
                ""
            ).strip(),

        "object_key":
            os.environ.get(
                "R2_EBOOK_OBJECT_KEY",
                ""
            ).strip(),

    }


    missing = [

        key

        for key, value
        in config.items()

        if not value

    ]


    if missing:

        raise RuntimeError(

            "Configuração R2 incompleta. "
            "Variáveis ausentes: "
            + ", ".join(missing)

        )


    return config

def get_kehai_r2_client():

    config = (
        get_kehai_r2_config()
    )


    endpoint_url = (
        config[
            "endpoint_url"
        ]
        .rstrip("/")
    )


    client = boto3.client(

        service_name=
            "s3",

        endpoint_url=
            endpoint_url,

        aws_access_key_id=
            config[
                "access_key_id"
            ],

        aws_secret_access_key=
            config[
                "secret_access_key"
            ],

        region_name=
            "auto",

    )


    return client

def diagnosticar_kehai_r2():

    config = (
        get_kehai_r2_config()
    )


    client = (
        get_kehai_r2_client()
    )


    bucket_name = (
        config[
            "bucket_name"
        ]
    )


    object_key = (
        config[
            "object_key"
        ]
    )


    resposta = (
        client.head_object(

            Bucket=
                bucket_name,

            Key=
                object_key,

        )
    )


    tamanho_bytes = int(
        resposta.get(
            "ContentLength",
            0
        )
        or 0
    )


    tamanho_mb = (
        tamanho_bytes
        /
        1024
        /
        1024
    )


    content_type = (
        resposta.get(
            "ContentType"
        )
        or
        "não informado"
    )


    print(
        "[KEHAI R2] "
        "Conectado: SIM"
    )


    print(
        "[KEHAI R2] "
        "Arquivo encontrado: SIM"
    )


    print(
        "[KEHAI R2] "
        f"Bucket: {bucket_name}"
    )


    print(
        "[KEHAI R2] "
        f"Objeto: {object_key}"
    )


    print(
        "[KEHAI R2] "
        f"Tamanho: "
        f"{tamanho_mb:.2f} MB "
        f"({tamanho_bytes} bytes)"
    )


    print(
        "[KEHAI R2] "
        f"Content-Type: "
        f"{content_type}"
    )


    return {

        "ok":
            True,

        "bucket":
            bucket_name,

        "object_key":
            object_key,

        "size_bytes":
            tamanho_bytes,

        "size_mb":
            round(
                tamanho_mb,
                2
            ),

        "content_type":
            content_type,

    }

def gerar_url_temporaria_ebook_kehai():

    config = (
        get_kehai_r2_config()
    )


    client = (
        get_kehai_r2_client()
    )


    url = (
        client.generate_presigned_url(

            ClientMethod=
                "get_object",

            Params={

                "Bucket":
                    config[
                        "bucket_name"
                    ],

                "Key":
                    config[
                        "object_key"
                    ],

            },

            ExpiresIn=
                KEHAI_R2_URL_EXPIRES_SECONDS,

        )
    )


    return url

# -----------------------------
# KEHAI - Produto digital
# -----------------------------

KEHAI_EBOOK_PRODUCT = {
    "code": "KEHAI-EBOOK",
    "title": "KEHAI - eBook",
    "quantity": 1,
    "unit_price_cents": 2990,
}    

def agora_iso():
    return datetime.now(timezone.utc).isoformat()


def normalizar_cep(value):
    cep = "".join(ch for ch in str(value or "") if ch.isdigit())
    return cep if len(cep) == 8 else None


def reais_para_centavos(value):
    try:
        decimal_value = Decimal(str(value)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Valor monetário inválido.")

    return int(decimal_value * 100)


def centavos_para_reais(cents):
    return float(
        (Decimal(int(cents)) / Decimal(100)).quantize(
            Decimal("0.01")
        )
    )


def get_kehai_db():
    os.makedirs(KEHAI_DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(
        KEHAI_DB_PATH,
        timeout=15,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def inicializar_banco_kehai():
    with get_kehai_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kehai_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_payment',

                product_code TEXT NOT NULL,
                product_title TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price_cents INTEGER NOT NULL,
                subtotal_cents INTEGER NOT NULL,

                shipping_service_id TEXT NOT NULL,
                shipping_service TEXT NOT NULL,
                shipping_company TEXT NOT NULL,
                shipping_price_cents INTEGER NOT NULL,
                shipping_delivery_days INTEGER,
                total_cents INTEGER NOT NULL,

                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_document TEXT,

                postal_code TEXT NOT NULL,
                street TEXT NOT NULL,
                address_number TEXT NOT NULL,
                complement TEXT,
                district TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,

                mp_preference_id TEXT,
                mp_payment_id TEXT,
                mp_payment_status TEXT,
                payment_confirmed_at TEXT,

                fulfillment_status TEXT NOT NULL DEFAULT 'pending',
                fulfillment_updated_at TEXT,
                tracking_code TEXT,
                shipped_at TEXT,
                delivered_at TEXT,
                internal_notes TEXT,

                invoice_key TEXT,
                me_shipment_id TEXT,
                me_shipment_status TEXT,
                me_label_url TEXT,
                me_cart_created_at TEXT,
                me_purchased_at TEXT,
                me_generated_at TEXT,
                me_printed_at TEXT,
                me_last_error TEXT,

                me_protocol TEXT,
                me_released_at TEXT,
                me_tracking_status TEXT,
                me_tracking_url TEXT,
                me_tracking_event_at TEXT,
                me_tracking_updated_at TEXT,
                me_tracking_source TEXT,
                me_webhook_event TEXT,
                me_tracking_last_error TEXT,

                email_confirmation_sent_at TEXT,
                email_confirmation_message_id TEXT,
                email_shipping_sent_at TEXT,
                email_shipping_message_id TEXT,
                email_delivery_sent_at TEXT,
                email_delivery_message_id TEXT,
                email_last_error TEXT
            )
            """
        )

        # Migração segura para bancos criados em versões anteriores.
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(kehai_orders)").fetchall()
        }

        migrations = {
            "payment_confirmed_at":
                "ALTER TABLE kehai_orders ADD COLUMN payment_confirmed_at TEXT",
            "fulfillment_status":
                "ALTER TABLE kehai_orders ADD COLUMN fulfillment_status TEXT NOT NULL DEFAULT 'pending'",
            "fulfillment_updated_at":
                "ALTER TABLE kehai_orders ADD COLUMN fulfillment_updated_at TEXT",
            "tracking_code":
                "ALTER TABLE kehai_orders ADD COLUMN tracking_code TEXT",
            "shipped_at":
                "ALTER TABLE kehai_orders ADD COLUMN shipped_at TEXT",
            "delivered_at":
                "ALTER TABLE kehai_orders ADD COLUMN delivered_at TEXT",
            "internal_notes":
                "ALTER TABLE kehai_orders ADD COLUMN internal_notes TEXT",
            "customer_document":
                "ALTER TABLE kehai_orders ADD COLUMN customer_document TEXT",
            "invoice_key":
                "ALTER TABLE kehai_orders ADD COLUMN invoice_key TEXT",
            "me_shipment_id":
                "ALTER TABLE kehai_orders ADD COLUMN me_shipment_id TEXT",
            "me_shipment_status":
                "ALTER TABLE kehai_orders ADD COLUMN me_shipment_status TEXT",
            "me_label_url":
                "ALTER TABLE kehai_orders ADD COLUMN me_label_url TEXT",
            "me_cart_created_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_cart_created_at TEXT",
            "me_purchased_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_purchased_at TEXT",
            "me_generated_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_generated_at TEXT",
            "me_printed_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_printed_at TEXT",
            "me_last_error":
                "ALTER TABLE kehai_orders ADD COLUMN me_last_error TEXT",
            "me_protocol":
                "ALTER TABLE kehai_orders ADD COLUMN me_protocol TEXT",
            "me_released_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_released_at TEXT",
            "me_tracking_status":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_status TEXT",
            "me_tracking_url":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_url TEXT",
            "me_tracking_event_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_event_at TEXT",
            "me_tracking_updated_at":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_updated_at TEXT",
            "me_tracking_source":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_source TEXT",
            "me_webhook_event":
                "ALTER TABLE kehai_orders ADD COLUMN me_webhook_event TEXT",
            "me_tracking_last_error":
                "ALTER TABLE kehai_orders ADD COLUMN me_tracking_last_error TEXT",
            "email_confirmation_sent_at":
                "ALTER TABLE kehai_orders ADD COLUMN email_confirmation_sent_at TEXT",
            "email_confirmation_message_id":
                "ALTER TABLE kehai_orders ADD COLUMN email_confirmation_message_id TEXT",
            "email_shipping_sent_at":
                "ALTER TABLE kehai_orders ADD COLUMN email_shipping_sent_at TEXT",
            "email_shipping_message_id":
                "ALTER TABLE kehai_orders ADD COLUMN email_shipping_message_id TEXT",
            "email_delivery_sent_at":
                "ALTER TABLE kehai_orders ADD COLUMN email_delivery_sent_at TEXT",
            "email_delivery_message_id":
                "ALTER TABLE kehai_orders ADD COLUMN email_delivery_message_id TEXT",
            "email_last_error":
                "ALTER TABLE kehai_orders ADD COLUMN email_last_error TEXT",
        }

        for column_name, statement in migrations.items():
            if column_name not in existing_columns:
                conn.execute(statement)

        # Backfill de marcos para pedidos criados antes desta versão.
        # Para pagamentos antigos, created_at é usado apenas como aproximação
        # visual quando não há data de aprovação armazenada.
        conn.execute(
            """
            UPDATE kehai_orders
            SET payment_confirmed_at = created_at
            WHERE status = 'paid'
              AND (payment_confirmed_at IS NULL OR payment_confirmed_at = '')
            """
        )

        conn.execute(
            """
            UPDATE kehai_orders
            SET me_released_at = COALESCE(me_purchased_at, me_tracking_event_at)
            WHERE (me_released_at IS NULL OR me_released_at = '')
              AND (
                    me_purchased_at IS NOT NULL
                    OR me_tracking_status IN (
                        'released', 'generated', 'posted', 'received',
                        'delivered', 'undelivered', 'paused', 'suspended'
                    )
                  )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kehai_orders_status "
            "ON kehai_orders(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kehai_orders_payment "
            "ON kehai_orders(mp_payment_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_kehai_orders_me_shipment "
            "ON kehai_orders(me_shipment_id)"
        )

    print(f"[KEHAI DB] Banco pronto em {KEHAI_DB_PATH}")


def criar_pedido_kehai(data):
    created_at = agora_iso()
    temp_number = f"TMP-{secrets.token_hex(10)}"

    with get_kehai_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO kehai_orders (
                order_number,
                created_at,
                updated_at,
                status,
                product_code,
                product_title,
                quantity,
                unit_price_cents,
                subtotal_cents,
                shipping_service_id,
                shipping_service,
                shipping_company,
                shipping_price_cents,
                shipping_delivery_days,
                total_cents,
                customer_name,
                customer_email,
                customer_phone,
                customer_document,
                postal_code,
                street,
                address_number,
                complement,
                district,
                city,
                state
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                temp_number,
                created_at,
                created_at,
                "awaiting_payment",
                data["product_code"],
                data["product_title"],
                data["quantity"],
                data["unit_price_cents"],
                data["subtotal_cents"],
                str(data["shipping_service_id"]),
                data["shipping_service"],
                data["shipping_company"],
                data["shipping_price_cents"],
                data.get("shipping_delivery_days"),
                data["total_cents"],
                data["customer_name"],
                data["customer_email"],
                data["customer_phone"],
                data.get("customer_document"),
                data["postal_code"],
                data["street"],
                data["address_number"],
                data.get("complement", ""),
                data["district"],
                data["city"],
                data["state"],
            ),
        )

        order_id = cursor.lastrowid
        date_part = datetime.now().strftime("%Y%m%d")
        order_number = f"KEHAI-{date_part}-{order_id:06d}"

        conn.execute(
            "UPDATE kehai_orders SET order_number = ? WHERE id = ?",
            (order_number, order_id),
        )

        row = conn.execute(
            "SELECT * FROM kehai_orders WHERE id = ?",
            (order_id,),
        ).fetchone()

    return dict(row)


def buscar_pedido_kehai(order_number):
    with get_kehai_db() as conn:
        row = conn.execute(
            "SELECT * FROM kehai_orders WHERE order_number = ?",
            (str(order_number or "").strip(),),
        ).fetchone()

    return dict(row) if row else None


def buscar_pedido_kehai_por_shipment_id(shipment_id):
    shipment_id = str(shipment_id or "").strip()
    if not shipment_id:
        return None

    with get_kehai_db() as conn:
        row = conn.execute(
            "SELECT * FROM kehai_orders WHERE me_shipment_id = ?",
            (shipment_id,),
        ).fetchone()

    return dict(row) if row else None


def atualizar_pedido_kehai(order_number, **fields):
    allowed = {
        "status",
        "updated_at",
        "mp_preference_id",
        "mp_payment_id",
        "mp_payment_status",
        "payment_confirmed_at",
        "fulfillment_status",
        "fulfillment_updated_at",
        "tracking_code",
        "shipped_at",
        "delivered_at",
        "internal_notes",
        "customer_document",
        "invoice_key",
        "me_shipment_id",
        "me_shipment_status",
        "me_label_url",
        "me_cart_created_at",
        "me_purchased_at",
        "me_generated_at",
        "me_printed_at",
        "me_last_error",
        "me_protocol",
        "me_released_at",
        "me_tracking_status",
        "me_tracking_url",
        "me_tracking_event_at",
        "me_tracking_updated_at",
        "me_tracking_source",
        "me_webhook_event",
        "me_tracking_last_error",
        "email_confirmation_sent_at",
        "email_confirmation_message_id",
        "email_shipping_sent_at",
        "email_shipping_message_id",
        "email_delivery_sent_at",
        "email_delivery_message_id",
        "email_last_error",
    }

    updates = {
        key: value
        for key, value in fields.items()
        if key in allowed
    }

    updates["updated_at"] = agora_iso()

    if not updates:
        return

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values()) + [order_number]

    with get_kehai_db() as conn:
        conn.execute(
            f"UPDATE kehai_orders SET {set_clause} WHERE order_number = ?",
            values,
        )

# =====================================================
# KEHAI - PEDIDOS DO EBOOK
# =====================================================

def inicializar_banco_ebook_kehai():

    with get_kehai_db() as conn:

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kehai_ebook_orders (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                order_number TEXT UNIQUE NOT NULL,

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'awaiting_payment',

                product_code TEXT NOT NULL,
                product_title TEXT NOT NULL,

                quantity INTEGER NOT NULL
                    DEFAULT 1,

                unit_price_cents INTEGER NOT NULL,
                subtotal_cents INTEGER NOT NULL,
                total_cents INTEGER NOT NULL,

                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL,

                mp_preference_id TEXT,
                mp_payment_id TEXT,
                mp_payment_status TEXT,
                payment_confirmed_at TEXT,

                download_token TEXT UNIQUE,
                download_count INTEGER NOT NULL
                    DEFAULT 0,

                download_last_at TEXT,

                email_access_sent_at TEXT,
                email_access_message_id TEXT,
                email_last_error TEXT

            )
            """
        )


        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_kehai_ebook_orders_status

            ON kehai_ebook_orders(status)
            """
        )


        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_kehai_ebook_orders_payment

            ON kehai_ebook_orders(mp_payment_id)
            """
        )


    print(
        "[KEHAI EBOOK DB] "
        "Tabela de pedidos digitais pronta."
    )


def criar_pedido_ebook_kehai(
    customer_name,
    customer_email,
):

    created_at = agora_iso()

    temp_number = (
        "EBTMP-"
        + secrets.token_hex(10)
    )


    download_token = (
        secrets.token_urlsafe(32)
    )


    product = KEHAI_EBOOK_PRODUCT


    quantity = product["quantity"]

    unit_price_cents = (
        product["unit_price_cents"]
    )

    subtotal_cents = (
        unit_price_cents
        *
        quantity
    )

    total_cents = subtotal_cents


    with get_kehai_db() as conn:

        cursor = conn.execute(
            """
            INSERT INTO kehai_ebook_orders (

                order_number,

                created_at,
                updated_at,

                status,

                product_code,
                product_title,

                quantity,

                unit_price_cents,
                subtotal_cents,
                total_cents,

                customer_name,
                customer_email,

                download_token

            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,

            (
                temp_number,

                created_at,
                created_at,

                "awaiting_payment",

                product["code"],
                product["title"],

                quantity,

                unit_price_cents,
                subtotal_cents,
                total_cents,

                customer_name,
                customer_email,

                download_token,
            ),
        )


        order_id = cursor.lastrowid


        date_part = (
            datetime.now()
            .strftime("%Y%m%d")
        )


        order_number = (
            f"KEHAI-EB-"
            f"{date_part}-"
            f"{order_id:06d}"
        )


        conn.execute(
            """
            UPDATE kehai_ebook_orders

            SET order_number = ?

            WHERE id = ?
            """,

            (
                order_number,
                order_id,
            ),
        )


        row = conn.execute(
            """
            SELECT *

            FROM kehai_ebook_orders

            WHERE id = ?
            """,

            (
                order_id,
            ),
        ).fetchone()


    return dict(row)


def buscar_pedido_ebook_kehai(
    order_number
):

    order_number = str(
        order_number or ""
    ).strip()


    if not order_number:

        return None


    with get_kehai_db() as conn:

        row = conn.execute(
            """
            SELECT *

            FROM kehai_ebook_orders

            WHERE order_number = ?
            """,

            (
                order_number,
            ),
        ).fetchone()


    return dict(row) if row else None

def buscar_pedido_ebook_por_token(
    download_token
):

    download_token = str(
        download_token
        or ""
    ).strip()


    if not download_token:

        return None


    with get_kehai_db() as conn:

        row = conn.execute(
            """
            SELECT *

            FROM kehai_ebook_orders

            WHERE download_token = ?
            """,

            (
                download_token,
            ),
        ).fetchone()


    return (
        dict(row)
        if row
        else None
    )


def atualizar_pedido_ebook_kehai(
    order_number,
    **fields,
):

    allowed = {

        "status",

        "mp_preference_id",
        "mp_payment_id",
        "mp_payment_status",

        "payment_confirmed_at",

        "download_count",
        "download_last_at",

        "email_access_sent_at",
        "email_access_message_id",
        "email_last_error",

    }


    updates = {

        key: value

        for key, value
        in fields.items()

        if key in allowed

    }


    updates["updated_at"] = agora_iso()


    set_clause = ", ".join(
        f"{key} = ?"
        for key in updates
    )


    values = (
        list(updates.values())
        +
        [order_number]
    )


    with get_kehai_db() as conn:

        conn.execute(

            f"""
            UPDATE kehai_ebook_orders

            SET {set_clause}

            WHERE order_number = ?
            """,

            values,
        )


# Cria a estrutura automaticamente quando o app sobe no Render/Gunicorn.
inicializar_banco_kehai()
inicializar_banco_ebook_kehai()

# =====================================================
# KEHAI EBOOK - DIAGNÓSTICO R2
# =====================================================

try:

    diagnosticar_kehai_r2()


except Exception as erro:

    print(
        "[KEHAI R2] "
        "Conectado: NÃO"
    )


    print(
        "[KEHAI R2] "
        f"Erro: "
        f"{type(erro).__name__}: "
        f"{erro}"
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

# ==========================================================
# KEHAI — LANDING PAGE DO EBOOK
# ==========================================================

@app.route("/kehai/ebook")
def kehai_ebook():
    return render_template("kehai_ebook.html")

# =====================================================
# KEHAI EBOOK - RETORNOS DO PAGAMENTO
# =====================================================

def _render_kehai_ebook_compra_status(
    page_kind
):

    order_number = str(
        request.args.get(
            "order"
        )
        or ""
    ).strip()


    payment_id = str(

        request.args.get(
            "payment_id"
        )

        or

        request.args.get(
            "collection_id"
        )

        or

        ""

    ).strip()


    pedido = (

        buscar_pedido_ebook_kehai(
            order_number
        )

        if order_number

        else None

    )


    # Confirma diretamente na API do Mercado Pago.
    if (
        payment_id
        and
        order_number
    ):

        try:

            pedido_sincronizado = (
                sincronizar_pagamento_ebook_kehai(

                    payment_id,

                    expected_order_number=
                        order_number,

                )
            )


            if pedido_sincronizado:

                pedido = (
                    pedido_sincronizado
                )


        except Exception as erro:

            print(
                "[KEHAI EBOOK RETORNO] "
                f"Falha ao sincronizar: "
                f"{erro}"
            )


    return render_template(

        "kehai_ebook_compra_status.html",

        page_kind=
            page_kind,

        pedido=
            pedido,

        payment_id=
            payment_id
            or None,

    )


@app.route(
    "/kehai/ebook/compra/sucesso"
)
def kehai_ebook_compra_sucesso():

    return (
        _render_kehai_ebook_compra_status(
            "success"
        )
    )


@app.route(
    "/kehai/ebook/compra/pendente"
)
def kehai_ebook_compra_pendente():

    return (
        _render_kehai_ebook_compra_status(
            "pending"
        )
    )


@app.route(
    "/kehai/ebook/compra/erro"
)
def kehai_ebook_compra_erro():

    return (
        _render_kehai_ebook_compra_status(
            "failure"
        )
    )

# =====================================================
# KEHAI EBOOK - ACESSO PROTEGIDO
# =====================================================

@app.route(
    "/kehai/ebook/acesso/<download_token>"
)
def kehai_ebook_acesso(
    download_token
):

    pedido = (
        buscar_pedido_ebook_por_token(
            download_token
        )
    )


    # ---------------------------------------------
    # TOKEN NÃO EXISTE
    # ---------------------------------------------

    if not pedido:

        return render_template(

            "kehai_ebook_acesso_status.html",

            access_status=
                "invalid",

            pedido=
                None,

        ), 404


    # ---------------------------------------------
    # PEDIDO NÃO ESTÁ PAGO
    # ---------------------------------------------

    if (
        pedido["status"]
        !=
        "paid"
    ):

        return render_template(

            "kehai_ebook_acesso_status.html",

            access_status=
                "not_paid",

            pedido=
                pedido,

        ), 403


    # ---------------------------------------------
    # LIMITE DE DOWNLOADS
    # ---------------------------------------------

    download_count = int(
        pedido.get(
            "download_count"
        )
        or 0
    )


    if (
        download_count
        >=
        KEHAI_EBOOK_DOWNLOAD_LIMIT
    ):

        print(
            "[KEHAI EBOOK DOWNLOAD] "
            f"Limite atingido: "
            f"{pedido['order_number']}"
        )


        return render_template(

            "kehai_ebook_acesso_status.html",

            access_status=
                "limit",

            pedido=
                pedido,

        ), 429


    # ---------------------------------------------
    # GERAR URL TEMPORÁRIA
    # ---------------------------------------------

    try:

        download_url = (
            gerar_url_temporaria_ebook_kehai()
        )


        novo_download_count = (
            download_count
            +
            1
        )


        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            download_count=
                novo_download_count,

            download_last_at=
                agora_iso(),

        )


        print(
            "[KEHAI EBOOK DOWNLOAD] "
            f"Acesso autorizado: "
            f"{pedido['order_number']} "
            f"download="
            f"{novo_download_count}/"
            f"{KEHAI_EBOOK_DOWNLOAD_LIMIT}"
        )


        return redirect(
            download_url
        )


    except Exception as erro:

        print(
            "[KEHAI EBOOK DOWNLOAD] "
            f"Erro ao gerar URL: "
            f"{type(erro).__name__}: "
            f"{erro}"
        )


        return render_template(

            "kehai_ebook_acesso_status.html",

            access_status=
                "error",

            pedido=
                pedido,

        ), 500

# =====================================================
# KEHAI - MELHOR ENVIO - FUNÇÕES DE FRETE
# =====================================================

def obter_opcoes_frete_kehai(cep_destino):
    cep_destino = normalizar_cep(cep_destino)
    if not cep_destino:
        raise ValueError("CEP inválido.")

    token_data = carregar_token_melhor_envio()
    if not token_data:
        raise RuntimeError("Melhor Envio ainda não autorizado.")

    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError("Token do Melhor Envio não encontrado.")

    product = KEHAI_PRODUCTS["physical"]

    payload = {
        "from": {
            "postal_code": KEHAI_ORIGIN_POSTAL_CODE,
        },
        "to": {
            "postal_code": cep_destino,
        },
        "products": [
            {
                "id": product["code"],
                "width": product["width"],
                "height": product["height"],
                "length": product["length"],
                "weight": product["weight"],
                "insurance_value": centavos_para_reais(
                    product["unit_price_cents"]
                ),
                "quantity": product["quantity"],
            }
        ],
        "options": {
            "receipt": False,
            "own_hand": False,
            "collect": False,
        },
    }

    url = (
        f"{MELHOR_ENVIO_BASE_URL}"
        "/api/v2/me/shipment/calculate"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": MELHOR_ENVIO_USER_AGENT,
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=20,
    )

    if response.status_code == 401:
        print(
            "[MELHOR ENVIO] Token expirado ou inválido. "
            "Tentando renovação automática."
        )

        novo_token_data = renovar_token_melhor_envio()
        novo_access_token = novo_token_data.get("access_token")

        if not novo_access_token:
            raise RuntimeError("Novo access token não recebido.")

        headers["Authorization"] = f"Bearer {novo_access_token}"

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=20,
        )

    if not response.ok:
        print(
            "[MELHOR ENVIO] Erro cotação: "
            f"{response.status_code} {response.text}"
        )
        raise RuntimeError("Não foi possível calcular o frete.")

    cotacoes = response.json()
    opcoes = []

    for cotacao in cotacoes:
        if cotacao.get("error"):
            continue

        preco_raw = (
            cotacao.get("custom_price")
            or cotacao.get("price")
        )
        prazo = (
            cotacao.get("custom_delivery_time")
            or cotacao.get("delivery_time")
        )
        company = cotacao.get("company") or {}

        try:
            preco_cents = reais_para_centavos(preco_raw)
        except ValueError:
            continue

        opcoes.append({
            "id": str(cotacao.get("id")),
            "servico": cotacao.get("name") or "Frete",
            "transportadora": company.get("name") or "Transportadora",
            "preco": f"{preco_cents / 100:.2f}",
            "preco_cents": preco_cents,
            "prazo_dias": prazo,
        })

    return cep_destino, opcoes

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
        "scope": MELHOR_ENVIO_SCOPES,
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


    salvar_token_melhor_envio(
        token_data
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
        dados = request.get_json(silent=True) or {}
        cep_destino, opcoes = obter_opcoes_frete_kehai(
            dados.get("cep", "")
        )

        return jsonify({
            "success": True,
            "cep": cep_destino,
            "opcoes": [
                {
                    "id": item["id"],
                    "servico": item["servico"],
                    "transportadora": item["transportadora"],
                    "preco": item["preco"],
                    "prazo_dias": item["prazo_dias"],
                }
                for item in opcoes
            ],
        })

    except ValueError as erro:
        return jsonify({
            "success": False,
            "error": str(erro),
        }), 400

    except Exception as erro:
        print(
            "[MELHOR ENVIO] "
            f"Erro inesperado na cotação: {erro}"
        )
        return jsonify({
            "success": False,
            "error": "Erro interno ao calcular o frete.",
        }), 500

# =====================================================
# KEHAI - CRIAÇÃO DE PEDIDO
# =====================================================

@app.route("/api/kehai/pedido", methods=["POST"])
def kehai_criar_pedido():
    try:
        dados = request.get_json(silent=True) or {}

        product_key = str(dados.get("product") or "physical").strip()
        product = KEHAI_PRODUCTS.get(product_key)
        if not product:
            return jsonify({
                "success": False,
                "error": "Produto inválido.",
            }), 400

        customer = dados.get("customer") or {}
        address = dados.get("address") or {}

        name = str(customer.get("name") or "").strip()
        email = str(customer.get("email") or "").strip().lower()
        phone = str(customer.get("phone") or "").strip()
        customer_document = somente_digitos(
            customer.get("document") or ""
        )

        postal_code = normalizar_cep(address.get("postal_code"))
        street = str(address.get("street") or "").strip()
        address_number = str(address.get("number") or "").strip()
        complement = str(address.get("complement") or "").strip()
        district = str(address.get("district") or "").strip()
        city = str(address.get("city") or "").strip()
        state = str(address.get("state") or "").strip().upper()

        required = {
            "Nome": name,
            "E-mail": email,
            "Telefone": phone,
            "CPF": customer_document,
            "CEP": postal_code,
            "Rua": street,
            "Número": address_number,
            "Bairro": district,
            "Cidade": city,
            "UF": state,
        }
        missing = [label for label, value in required.items() if not value]
        if missing:
            return jsonify({
                "success": False,
                "error": "Preencha: " + ", ".join(missing) + ".",
            }), 400

        if len(customer_document) != 11:
            return jsonify({
                "success": False,
                "error": "Informe um CPF válido com 11 dígitos.",
            }), 400

        shipping_service_id = str(
            dados.get("shipping_service_id") or ""
        ).strip()
        if not shipping_service_id:
            return jsonify({
                "success": False,
                "error": "Selecione uma opção de frete.",
            }), 400

        _, opcoes = obter_opcoes_frete_kehai(postal_code)
        frete = next(
            (
                item
                for item in opcoes
                if str(item["id"]) == shipping_service_id
            ),
            None,
        )

        if not frete:
            return jsonify({
                "success": False,
                "error": "Opção de frete inválida ou indisponível.",
            }), 400

        unit_price_cents = product["unit_price_cents"]
        quantity = product["quantity"]
        subtotal_cents = unit_price_cents * quantity
        shipping_price_cents = frete["preco_cents"]
        total_cents = subtotal_cents + shipping_price_cents

        pedido = criar_pedido_kehai({
            "product_code": product["code"],
            "product_title": product["title"],
            "quantity": quantity,
            "unit_price_cents": unit_price_cents,
            "subtotal_cents": subtotal_cents,
            "shipping_service_id": frete["id"],
            "shipping_service": frete["servico"],
            "shipping_company": frete["transportadora"],
            "shipping_price_cents": shipping_price_cents,
            "shipping_delivery_days": frete["prazo_dias"],
            "total_cents": total_cents,
            "customer_name": name,
            "customer_email": email,
            "customer_phone": phone,
            "customer_document": customer_document,
            "postal_code": postal_code,
            "street": street,
            "address_number": address_number,
            "complement": complement,
            "district": district,
            "city": city,
            "state": state,
        })

        return jsonify({
            "success": True,
            "order_number": pedido["order_number"],
            "status": pedido["status"],
            "subtotal": f"{pedido['subtotal_cents'] / 100:.2f}",
            "frete": f"{pedido['shipping_price_cents'] / 100:.2f}",
            "total": f"{pedido['total_cents'] / 100:.2f}",
        }), 201

    except Exception as erro:
        print(f"[KEHAI PEDIDO] Erro ao criar pedido: {erro}")
        return jsonify({
            "success": False,
            "error": "Não foi possível criar o pedido.",
        }), 500

# =====================================================
# KEHAI - CHECKOUT DIGITAL DO EBOOK
# =====================================================

@app.route(
    "/api/kehai/ebook/checkout",
    methods=["POST"],
)
def kehai_ebook_checkout():

    try:

        dados = (
            request.get_json(
                silent=True
            )
            or {}
        )


        customer = (
            dados.get("customer")
            or {}
        )


        name = str(
            customer.get("name")
            or ""
        ).strip()


        email = str(
            customer.get("email")
            or ""
        ).strip().lower()


        email_confirmation = str(
            customer.get(
                "email_confirmation"
            )
            or ""
        ).strip().lower()


        # ---------------------------------------------
        # VALIDAÇÕES
        # ---------------------------------------------

        if len(name) < 2:

            return jsonify({
                "success": False,
                "error":
                    "Informe seu nome."
            }), 400


        email_pattern = (
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        )


        if not re.match(
            email_pattern,
            email
        ):

            return jsonify({
                "success": False,
                "error":
                    "Informe um e-mail válido."
            }), 400


        if (
            email
            !=
            email_confirmation
        ):

            return jsonify({
                "success": False,
                "error":
                    "Os dois e-mails precisam ser iguais."
            }), 400


        # ---------------------------------------------
        # CRIAR PEDIDO DIGITAL
        # ---------------------------------------------

        pedido = (
            criar_pedido_ebook_kehai(
                customer_name=name,
                customer_email=email,
            )
        )


        # ---------------------------------------------
        # MERCADO PAGO
        # ---------------------------------------------

        sdk = get_mercadopago_sdk()


        preference_data = {

            "items": [
                {
                    "id":
                        pedido[
                            "product_code"
                        ],

                    "title":
                        pedido[
                            "product_title"
                        ],

                    "quantity":
                        pedido[
                            "quantity"
                        ],

                    "currency_id":
                        "BRL",

                    "unit_price":
                        centavos_para_reais(
                            pedido[
                                "unit_price_cents"
                            ]
                        ),
                }
            ],


            "payer": {

                "name":
                    pedido[
                        "customer_name"
                    ],

                "email":
                    pedido[
                        "customer_email"
                    ],

            },


            "back_urls": {

                "success": (
                    "https://www.stegie.com.br/"
                    "kehai/ebook/compra/sucesso"
                    f"?order={pedido['order_number']}"
                ),

                "failure": (
                    "https://www.stegie.com.br/"
                    "kehai/ebook/compra/erro"
                    f"?order={pedido['order_number']}"
                ),

                "pending": (
                    "https://www.stegie.com.br/"
                    "kehai/ebook/compra/pendente"
                    f"?order={pedido['order_number']}"
                ),

            },


            "auto_return":
                "approved",


            "external_reference":
                pedido[
                    "order_number"
                ],

        }


        preference_response = (
            sdk
            .preference()
            .create(
                preference_data
            )
        )


        preference = (
            preference_response.get(
                "response",
                {}
            )
        )


        preference_id = (
            preference.get("id")
        )


        checkout_url = (
            preference.get(
                "init_point"
            )
        )


        sandbox_checkout_url = (
            preference.get(
                "sandbox_init_point"
            )
        )


        if (
            not preference_id
            or
            not checkout_url
        ):

            atualizar_pedido_ebook_kehai(
                pedido[
                    "order_number"
                ],

                status=
                    "checkout_error",
            )


            raise RuntimeError(
                "Mercado Pago não retornou "
                "uma preferência válida."
            )


        # ---------------------------------------------
        # SALVAR PREFERÊNCIA
        # ---------------------------------------------

        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            status=
                "checkout_created",

            mp_preference_id=
                preference_id,

        )


        print(
            "[KEHAI EBOOK] "
            f"Pedido criado: "
            f"{pedido['order_number']} "
            f"- {pedido['customer_email']}"
        )


        return jsonify({

            "success":
                True,

            "order_number":
                pedido[
                    "order_number"
                ],

            "preference_id":
                preference_id,

            "checkout_url":
                checkout_url,

            "sandbox_checkout_url":
                sandbox_checkout_url,

        }), 201


    except Exception as erro:

        print(
            "[KEHAI EBOOK] "
            f"Erro ao iniciar checkout: "
            f"{erro}"
        )


        return jsonify({

            "success":
                False,

            "error":
                "Não foi possível iniciar "
                "o pagamento agora."

        }), 500

# =====================================================
# KEHAI - CHECKOUT MERCADO PAGO
# =====================================================

@app.route("/api/kehai/checkout", methods=["POST"])
def kehai_checkout():
    try:
        dados = request.get_json(silent=True) or {}
        order_number = str(dados.get("order_number") or "").strip()

        # Compatibilidade temporária com a landing atual durante Sandbox.
        if not order_number:
            produto = dados.get("product")
            if produto == "physical" and "sandbox" in MELHOR_ENVIO_BASE_URL.lower():
                sdk = get_mercadopago_sdk()
                product = KEHAI_PRODUCTS["physical"]
                preference_data = {
                    "items": [
                        {
                            "title": product["title"],
                            "quantity": product["quantity"],
                            "currency_id": "BRL",
                            "unit_price": centavos_para_reais(
                                product["unit_price_cents"]
                            ),
                        }
                    ],
                    "back_urls": {
                        "success": "https://www.stegie.com.br/kehai/compra/sucesso",
                        "failure": "https://www.stegie.com.br/kehai/compra/erro",
                        "pending": "https://www.stegie.com.br/kehai/compra/pendente",
                    },
                    "auto_return": "approved",
                    "external_reference": "KEHAI-physical-test",
                }

                preference_response = sdk.preference().create(preference_data)
                preference = preference_response.get("response", {})

                return jsonify({
                    "success": True,
                    "preference_id": preference.get("id"),
                    "checkout_url": preference.get("init_point"),
                    "sandbox_checkout_url": preference.get("sandbox_init_point"),
                    "legacy_test": True,
                })

            return jsonify({
                "success": False,
                "error": "Pedido não informado.",
            }), 400

        pedido = buscar_pedido_kehai(order_number)
        if not pedido:
            return jsonify({
                "success": False,
                "error": "Pedido não encontrado.",
            }), 404

        if pedido["status"] == "paid":
            return jsonify({
                "success": False,
                "error": "Este pedido já está pago.",
            }), 409

        sdk = get_mercadopago_sdk()

        preference_data = {
            "items": [
                {
                    "title": pedido["product_title"],
                    "quantity": pedido["quantity"],
                    "currency_id": "BRL",
                    "unit_price": centavos_para_reais(
                        pedido["unit_price_cents"]
                    ),
                }
            ],
            "payer": {
                "name": pedido["customer_name"],
                "email": pedido["customer_email"],
            },
            "shipments": {
                "cost": centavos_para_reais(
                    pedido["shipping_price_cents"]
                ),
                "receiver_address": {
                    "zip_code": pedido["postal_code"],
                    "street_name": pedido["street"],
                    "street_number": pedido["address_number"],
                    "floor": pedido["complement"] or "",
                    "city_name": pedido["city"],
                    "state_name": pedido["state"],
                },
            },
            "back_urls": {
                "success": (
                    "https://www.stegie.com.br/kehai/compra/sucesso"
                    f"?order={pedido['order_number']}"
                ),
                "failure": (
                    "https://www.stegie.com.br/kehai/compra/erro"
                    f"?order={pedido['order_number']}"
                ),
                "pending": (
                    "https://www.stegie.com.br/kehai/compra/pendente"
                    f"?order={pedido['order_number']}"
                ),
            },
            "auto_return": "approved",
            "external_reference": pedido["order_number"],
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response.get("response", {})
        preference_id = preference.get("id")
        checkout_url = preference.get("init_point")

        if not preference_id or not checkout_url:
            raise RuntimeError(
                "Mercado Pago não retornou uma preferência válida."
            )

        atualizar_pedido_kehai(
            pedido["order_number"],
            status="checkout_created",
            mp_preference_id=preference_id,
        )

        return jsonify({
            "success": True,
            "order_number": pedido["order_number"],
            "preference_id": preference_id,
            "checkout_url": checkout_url,
            "sandbox_checkout_url": preference.get("sandbox_init_point"),
        })

    except Exception as erro:
        print(f"[MERCADO PAGO] Erro ao criar checkout: {erro}")
        return jsonify({
            "success": False,
            "error": "Não foi possível iniciar o pagamento.",
        }), 500

# =====================================================
# KEHAI - SINCRONIZAÇÃO DO RETORNO DO MERCADO PAGO
# =====================================================

def _mp_em_centavos(valor):
    if valor is None:
        return None

    try:
        return reais_para_centavos(valor)
    except (ValueError, TypeError):
        return None


def sincronizar_pagamento_kehai(payment_id, expected_order_number=None):
    """
    Confirma o pagamento diretamente na API do Mercado Pago.

    É usado na página de retorno para que a experiência do comprador
    não dependa da ordem de chegada entre redirect e webhook.
    O webhook continua sendo a confirmação assíncrona principal.
    """
    payment_id = str(payment_id or "").strip()

    if not payment_id:
        return None

    sdk = get_mercadopago_sdk()
    pagamento_response = sdk.payment().get(payment_id)
    pagamento = pagamento_response.get("response", {}) or {}

    status = pagamento.get("status")
    external_reference = pagamento.get("external_reference")
    transaction_amount = pagamento.get("transaction_amount")
    transaction_details = pagamento.get("transaction_details") or {}
    total_paid_amount = transaction_details.get("total_paid_amount")

    merchant_order_id = (pagamento.get("order") or {}).get("id")
    merchant_order = {}

    if merchant_order_id:
        try:
            merchant_response = requests.get(
                (
                    "https://api.mercadopago.com/"
                    f"merchant_orders/{merchant_order_id}"
                ),
                headers={
                    "Authorization": f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
                    "Accept": "application/json",
                },
                timeout=20,
            )

            if merchant_response.ok:
                merchant_order = merchant_response.json()
        except Exception as erro:
            print(
                "[MERCADO PAGO RETORNO] "
                f"Merchant Order indisponível: {erro}"
            )

    merchant_external_reference = merchant_order.get("external_reference")
    if merchant_external_reference:
        external_reference = merchant_external_reference

    if (
        expected_order_number
        and
        str(external_reference or "") != str(expected_order_number)
    ):
        print(
            "[MERCADO PAGO RETORNO] "
            "external_reference divergente. "
            f"esperado={expected_order_number} "
            f"recebido={external_reference}"
        )
        return buscar_pedido_kehai(expected_order_number)

    
    pedido = buscar_pedido_kehai(external_reference)
    if not pedido:
        return None

    transaction_amount_cents = _mp_em_centavos(transaction_amount)
    total_paid_amount_cents = _mp_em_centavos(total_paid_amount)
    merchant_total_cents = _mp_em_centavos(
        merchant_order.get("total_amount")
    )
    merchant_paid_cents = _mp_em_centavos(
        merchant_order.get("paid_amount")
    )
    merchant_shipping_cents = _mp_em_centavos(
        merchant_order.get("shipping_cost")
    )
    merchant_order_status = merchant_order.get("order_status")

    order_status = pedido["status"]

    if status == "approved":
        checks = [
            total_paid_amount_cents == pedido["total_cents"],
            (
                transaction_amount_cents is None
                or transaction_amount_cents == pedido["subtotal_cents"]
            ),
            (
                merchant_total_cents is None
                or merchant_total_cents == pedido["subtotal_cents"]
            ),
            (
                merchant_paid_cents is None
                or merchant_paid_cents == pedido["subtotal_cents"]
            ),
            (
                merchant_shipping_cents is None
                or merchant_shipping_cents == pedido["shipping_price_cents"]
            ),
            merchant_order_status in {None, "paid"},
        ]

        order_status = (
            "paid"
            if all(checks)
            else "payment_amount_mismatch"
        )

    elif status in {"pending", "in_process", "in_mediation"}:
        if pedido["status"] != "paid":
            order_status = "payment_pending"

    elif status in {"rejected", "cancelled"}:
        if pedido["status"] != "paid":
            order_status = "payment_failed"

    elif status in {"refunded", "charged_back"}:
        order_status = status

    payment_confirmed_at = pedido.get("payment_confirmed_at")
    if order_status == "paid" and not payment_confirmed_at:
        payment_confirmed_at = (
            pagamento.get("date_approved")
            or pagamento.get("date_last_updated")
            or agora_iso()
        )

    status_anterior = pedido.get("status")

    atualizar_pedido_kehai(
        pedido["order_number"],
        status=order_status,
        mp_payment_id=payment_id,
        mp_payment_status=status,
        payment_confirmed_at=payment_confirmed_at,
    )

    pedido_atualizado = buscar_pedido_kehai(pedido["order_number"])

    if order_status == "paid" and status_anterior != "paid":
        tentar_email_kehai(
            pedido_atualizado,
            "confirmation",
        )

    return buscar_pedido_kehai(pedido["order_number"])



def email_kehai_configurado():
    return bool(
        BREVO_API_KEY
        and KEHAI_EMAIL_FROM
        and KEHAI_EMAIL_FROM_NAME
    )


def _email_texto_kehai(pedido, tipo):
    order = pedido.get("order_number") or "—"
    nome = pedido.get("customer_name") or "Cliente"
    tracking = pedido.get("tracking_code") or "Aguardando transportadora"
    tracking_url = pedido.get("me_tracking_url") or ""

    if tipo == "confirmation":
        return (
            f"Olá, {nome}.\n\n"
            f"Seu pedido {order} foi confirmado com sucesso.\n"
            f"Total: {formatar_brl_centavos(pedido.get('total_cents'))}\n"
            f"Frete: {pedido.get('shipping_service') or '—'} — "
            f"{pedido.get('shipping_delivery_days') or '—'} dias úteis.\n\n"
            "Agora seu exemplar seguirá para preparação e postagem.\n\n"
            "KEHAI — Reconheça valor antes que ele se perca."
        )

    if tipo == "shipping":
        extra = f"\nAcompanhe: {tracking_url}" if tracking_url else ""
        return (
            f"Olá, {nome}.\n\n"
            f"Seu pedido {order} foi postado.\n"
            f"Código de rastreamento: {tracking}.{extra}\n\n"
            "Você pode acompanhar a entrega até o recebimento.\n\n"
            "KEHAI — Reconheça valor antes que ele se perca."
        )

    if tipo == "delivery":
        return (
            f"Olá, {nome}.\n\n"
            f"O Melhor Envio informou que o pedido {order} foi entregue.\n\n"
            "Esperamos que o KEHAI acompanhe você em novas decisões, "
            "conversas e formas de reconhecer valor.\n\n"
            "KEHAI — Reconheça valor antes que ele se perca."
        )

    raise ValueError("Tipo de e-mail KEHAI inválido.")


def _email_assunto_kehai(pedido, tipo):
    order = pedido.get("order_number") or "KEHAI"

    assuntos = {
        "confirmation": f"Pedido confirmado — {order}",
        "shipping": f"Seu KEHAI foi enviado — {order}",
        "delivery": f"Seu KEHAI foi entregue — {order}",
    }

    if tipo not in assuntos:
        raise ValueError("Tipo de e-mail KEHAI inválido.")

    return assuntos[tipo]


def _email_template_kehai(tipo):
    templates = {
        "confirmation": "emails/kehai_order_confirmed.html",
        "shipping": "emails/kehai_order_shipped.html",
        "delivery": "emails/kehai_order_delivered.html",
    }

    if tipo not in templates:
        raise ValueError("Tipo de e-mail KEHAI inválido.")

    return templates[tipo]


def _campos_email_kehai(tipo):
    campos = {
        "confirmation": (
            "email_confirmation_sent_at",
            "email_confirmation_message_id",
        ),
        "shipping": (
            "email_shipping_sent_at",
            "email_shipping_message_id",
        ),
        "delivery": (
            "email_delivery_sent_at",
            "email_delivery_message_id",
        ),
    }

    if tipo not in campos:
        raise ValueError("Tipo de e-mail KEHAI inválido.")

    return campos[tipo]


def enviar_email_transacional_kehai(pedido, tipo, *, force=False):
    """
    Envia um e-mail transacional via Brevo.

    - Idempotente por padrão: não reenvia o mesmo marco duas vezes.
    - force=True é reservado ao painel administrativo para reenvio manual.
    - Uma falha de e-mail nunca quebra pagamento, webhook ou rastreamento.
    """
    if not pedido:
        return {
            "ok": False,
            "skipped": True,
            "reason": "pedido_inexistente",
        }

    sent_field, message_field = _campos_email_kehai(tipo)

    if not force and pedido.get(sent_field):
        return {
            "ok": True,
            "skipped": True,
            "reason": "ja_enviado",
            "sent_at": pedido.get(sent_field),
        }

    destinatario = str(pedido.get("customer_email") or "").strip()
    if not destinatario or "@" not in destinatario:
        erro = "O pedido não possui um e-mail de destinatário válido."
        atualizar_pedido_kehai(
            pedido["order_number"],
            email_last_error=erro,
        )
        return {
            "ok": False,
            "skipped": True,
            "reason": "email_invalido",
            "error": erro,
        }

    if not email_kehai_configurado():
        erro = (
            "E-mail transacional não configurado no Render. "
            "Verifique BREVO_API_KEY e KEHAI_EMAIL_FROM."
        )
        atualizar_pedido_kehai(
            pedido["order_number"],
            email_last_error=erro,
        )
        return {
            "ok": False,
            "skipped": True,
            "reason": "nao_configurado",
            "error": erro,
        }

    assunto = _email_assunto_kehai(pedido, tipo)

    try:
        html_content = render_template(
            _email_template_kehai(tipo),
            pedido=contexto_admin_pedido_kehai(pedido),
        )

        payload = {
            "sender": {
                "name": KEHAI_EMAIL_FROM_NAME,
                "email": KEHAI_EMAIL_FROM,
            },
            "to": [
                {
                    "name": pedido.get("customer_name") or "",
                    "email": destinatario,
                }
            ],
            "subject": assunto,
            "htmlContent": html_content,
            "textContent": _email_texto_kehai(pedido, tipo),
            "tags": [
                "kehai",
                f"kehai-{tipo}",
            ],
            "headers": {
                "X-KEHAI-Order": str(pedido.get("order_number") or ""),
            },
        }

        if KEHAI_EMAIL_REPLY_TO:
            payload["replyTo"] = {
                "email": KEHAI_EMAIL_REPLY_TO,
                "name": KEHAI_EMAIL_FROM_NAME,
            }

        response = requests.post(
            KEHAI_EMAIL_BASE_URL,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": BREVO_API_KEY,
            },
            json=payload,
            timeout=20,
        )

        if not response.ok:
            detalhe = response.text[:1200]
            raise RuntimeError(
                f"Brevo HTTP {response.status_code}: {detalhe}"
            )

        try:
            body = response.json()
        except ValueError:
            body = {}

        message_id = str(
            body.get("messageId")
            or body.get("message_id")
            or ""
        ).strip()

        sent_at = agora_iso()

        fields = {
            sent_field: sent_at,
            message_field: message_id or None,
            "email_last_error": None,
        }
        atualizar_pedido_kehai(
            pedido["order_number"],
            **fields,
        )

        print(
            "[KEHAI EMAIL] "
            f"tipo={tipo} order={pedido['order_number']} "
            f"destino={destinatario} message_id={message_id or '—'}"
        )

        return {
            "ok": True,
            "skipped": False,
            "message_id": message_id,
            "sent_at": sent_at,
        }

    except Exception as exc:
        erro = str(exc)[:1600]

        atualizar_pedido_kehai(
            pedido["order_number"],
            email_last_error=erro,
        )

        print(
            "[KEHAI EMAIL] "
            f"Falha tipo={tipo} order={pedido['order_number']}: {erro}"
        )

        return {
            "ok": False,
            "skipped": False,
            "error": erro,
        }


def tentar_email_kehai(pedido, tipo):
    """
    Wrapper seguro para eventos automáticos.
    Nunca propaga exceção para Mercado Pago/Melhor Envio.
    """
    try:
        return enviar_email_transacional_kehai(
            pedido,
            tipo,
            force=False,
        )
    except Exception as exc:
        print(
            "[KEHAI EMAIL] "
            f"Erro inesperado no disparo automático: {exc}"
        )
        return {
            "ok": False,
            "error": str(exc),
        }

# =====================================================
# KEHAI EBOOK - E-MAIL DE ACESSO
# =====================================================

def reservar_envio_email_acesso_ebook_kehai(
    order_number
):

    marcador = (
        "sending:"
        + secrets.token_hex(8)
    )


    with get_kehai_db() as conn:

        cursor = conn.execute(
            """
            UPDATE kehai_ebook_orders

            SET
                email_access_sent_at = ?,
                updated_at = ?

            WHERE order_number = ?

              AND (
                    email_access_sent_at IS NULL
                    OR email_access_sent_at = ''
                  )
            """,

            (
                marcador,
                agora_iso(),
                order_number,
            ),
        )


        reservado = (
            cursor.rowcount == 1
        )


    return reservado


def url_acesso_ebook_kehai(
    pedido
):

    token = str(
        pedido.get(
            "download_token"
        )
        or ""
    ).strip()


    if not token:

        raise RuntimeError(
            "Pedido do eBook não possui "
            "token de acesso."
        )


    return (
        f"{KEHAI_PUBLIC_BASE_URL}"
        f"/kehai/ebook/acesso/{token}"
    )


def texto_email_acesso_ebook_kehai(
    pedido,
    access_url,
):

    nome = (
        pedido.get(
            "customer_name"
        )
        or
        "Cliente"
    )


    order_number = (
        pedido.get(
            "order_number"
        )
        or
        "KEHAI"
    )


    return (
        f"Olá, {nome}.\n\n"
        "Seu pagamento foi confirmado e "
        "seu eBook KEHAI já está disponível.\n\n"
        "Acesse seu eBook pelo link abaixo:\n\n"
        f"{access_url}\n\n"
        f"Pedido: {order_number}\n\n"
        "Este é um link pessoal de acesso. "
        "Evite compartilhá-lo.\n\n"
        "Boa leitura.\n\n"
        "KEHAI — A liderança que reconhece "
        "valor antes que ele se perca."
    )


def enviar_email_acesso_ebook_kehai(
    pedido
):

    if not pedido:

        return {
            "ok": False,
            "skipped": True,
            "reason": "pedido_inexistente",
        }


    if (
        pedido.get("status")
        !=
        "paid"
    ):

        return {
            "ok": False,
            "skipped": True,
            "reason":
                "pagamento_nao_confirmado",
        }


    # ---------------------------------------------
    # E-MAIL JÁ ENVIADO
    # ---------------------------------------------

    sent_at = str(
        pedido.get(
            "email_access_sent_at"
        )
        or ""
    ).strip()


    if sent_at:

        print(
            "[KEHAI EBOOK EMAIL] "
            f"Envio ignorado: "
            f"{pedido['order_number']} "
            "já possui registro de envio."
        )


        return {
            "ok": True,
            "skipped": True,
            "reason": "ja_enviado",
        }


    destinatario = str(
        pedido.get(
            "customer_email"
        )
        or ""
    ).strip()


    if (
        not destinatario
        or
        "@" not in destinatario
    ):

        erro = (
            "Pedido do eBook não possui "
            "e-mail válido."
        )


        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            email_last_error=
                erro,

        )


        return {
            "ok": False,
            "skipped": True,
            "reason": "email_invalido",
        }


    if not email_kehai_configurado():

        erro = (
            "Brevo não configurado. "
            "Verifique BREVO_API_KEY e "
            "KEHAI_EMAIL_FROM."
        )


        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            email_last_error=
                erro,

        )


        return {
            "ok": False,
            "skipped": True,
            "reason": "nao_configurado",
        }


    # ---------------------------------------------
    # RESERVA ATÔMICA
    #
    # Impede webhook e página de retorno
    # de dispararem dois e-mails ao mesmo tempo.
    # ---------------------------------------------

    reservado = (
        reservar_envio_email_acesso_ebook_kehai(
            pedido[
                "order_number"
            ]
        )
    )


    if not reservado:

        print(
            "[KEHAI EBOOK EMAIL] "
            f"Envio ignorado: "
            f"{pedido['order_number']} "
            "já foi reservado/enviado."
        )


        return {
            "ok": True,
            "skipped": True,
            "reason": "ja_reservado",
        }


    try:

        access_url = (
            url_acesso_ebook_kehai(
                pedido
            )
        )


        html_content = (
            render_template(

                "emails/"
                "kehai_ebook_access.html",

                pedido=
                    pedido,

                access_url=
                    access_url,

            )
        )


        subject = (
            "Seu eBook KEHAI "
            "está disponível"
        )


        payload = {

            "sender": {

                "name":
                    KEHAI_EMAIL_FROM_NAME,

                "email":
                    KEHAI_EMAIL_FROM,

            },


            "to": [
                {

                    "name":
                        pedido.get(
                            "customer_name"
                        )
                        or "",

                    "email":
                        destinatario,

                }
            ],


            "subject":
                subject,


            "htmlContent":
                html_content,


            "textContent":
                texto_email_acesso_ebook_kehai(
                    pedido,
                    access_url,
                ),


            "tags": [
                "kehai",
                "kehai-ebook",
                "kehai-ebook-access",
            ],


            "headers": {

                "X-KEHAI-Order":
                    str(
                        pedido.get(
                            "order_number"
                        )
                        or ""
                    ),

            },

        }


        if KEHAI_EMAIL_REPLY_TO:

            payload["replyTo"] = {

                "email":
                    KEHAI_EMAIL_REPLY_TO,

                "name":
                    KEHAI_EMAIL_FROM_NAME,

            }


        response = requests.post(

            KEHAI_EMAIL_BASE_URL,

            headers={

                "accept":
                    "application/json",

                "content-type":
                    "application/json",

                "api-key":
                    BREVO_API_KEY,

            },

            json=
                payload,

            timeout=
                20,

        )


        if not response.ok:

            detalhe = (
                response.text[:1200]
            )


            raise RuntimeError(

                f"Brevo HTTP "
                f"{response.status_code}: "
                f"{detalhe}"

            )


        try:

            body = (
                response.json()
            )

        except ValueError:

            body = {}


        message_id = str(

            body.get(
                "messageId"
            )

            or

            body.get(
                "message_id"
            )

            or

            ""

        ).strip()


        sent_at = agora_iso()


        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            email_access_sent_at=
                sent_at,

            email_access_message_id=
                message_id
                or None,

            email_last_error=
                None,

        )


        print(

            "[KEHAI EBOOK EMAIL] "
            f"Enviado: "
            f"{pedido['order_number']} "
            f"destino={destinatario} "
            f"message_id="
            f"{message_id or '—'}"

        )


        return {

            "ok":
                True,

            "skipped":
                False,

            "message_id":
                message_id,

            "sent_at":
                sent_at,

        }


    except Exception as erro:

        detalhe = str(
            erro
        )[:1600]


        # Libera uma futura tentativa,
        # porque o envio não foi concluído.
        atualizar_pedido_ebook_kehai(

            pedido[
                "order_number"
            ],

            email_access_sent_at=
                None,

            email_access_message_id=
                None,

            email_last_error=
                detalhe,

        )


        print(

            "[KEHAI EBOOK EMAIL] "
            f"Falha: "
            f"{pedido['order_number']} "
            f"{detalhe}"

        )


        return {

            "ok":
                False,

            "skipped":
                False,

            "error":
                detalhe,

        }


def tentar_email_acesso_ebook_kehai(
    pedido
):

    try:

        return (
            enviar_email_acesso_ebook_kehai(
                pedido
            )
        )


    except Exception as erro:

        print(

            "[KEHAI EBOOK EMAIL] "
            "Erro inesperado: "
            f"{erro}"

        )


        return {

            "ok":
                False,

            "error":
                str(erro),

        }

def formatar_brl_centavos(cents):
    valor = Decimal(int(cents or 0)) / Decimal(100)
    return f"R$ {valor:.2f}".replace(".", ",")


def contexto_pedido_kehai(pedido):
    if not pedido:
        return None

    contexto = dict(pedido)
    contexto["subtotal_formatado"] = formatar_brl_centavos(
        pedido["subtotal_cents"]
    )
    contexto["frete_formatado"] = formatar_brl_centavos(
        pedido["shipping_price_cents"]
    )
    contexto["total_formatado"] = formatar_brl_centavos(
        pedido["total_cents"]
    )
    return contexto


FULFILLMENT_LABELS = {
    "pending": "Aguardando preparação",
    "preparing": "Em preparação",
    "ready_to_ship": "Pronto para envio",
    "shipped": "Enviado",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
}


MELHOR_ENVIO_TRACKING_LABELS = {
    "pending": "Pendente",
    "released": "Frete liberado",
    "generated": "Etiqueta pronta",
    "received": "Recebido no ponto de distribuição",
    "posted": "Postado",
    "delivered": "Entregue",
    "cancelled": "Cancelado",
    "canceled": "Cancelado",
    "undelivered": "Não entregue",
    "paused": "Entrega pausada",
    "suspended": "Entrega suspensa",
}


MELHOR_ENVIO_EVENT_LABELS = {
    "order.created": "Envio criado no Melhor Envio",
    "order.pending": "Envio retornou ao carrinho",
    "order.released": "Frete liberado pelo Melhor Envio",
    "order.generated": "Etiqueta gerada e pronta",
    "order.received": "Encomenda recebida em ponto de distribuição",
    "order.posted": "Objeto postado",
    "order.delivered": "Entrega confirmada",
    "order.cancelled": "Envio cancelado",
    "order.undelivered": "Tentativa de entrega sem sucesso",
    "order.paused": "Entrega pausada — requer atenção",
    "order.suspended": "Entrega suspensa",
}


def label_evento_melhor_envio(event):
    event = str(event or "").strip()
    if not event:
        return "Aguardando nova atualização"
    return MELHOR_ENVIO_EVENT_LABELS.get(
        event,
        event.replace("order.", "").replace("_", " ").capitalize(),
    )


def label_origem_rastreamento(source):
    source = str(source or "").strip().lower()
    if source == "webhook":
        return "Atualização automática"
    if source == "api":
        return "Consulta manual"
    return "—" if not source else source.capitalize()


def formatar_data_hora_br(value):
    """Converte timestamps ISO/UTC para horário de Brasília."""
    text = str(value or "").strip()
    if not text:
        return "—"

    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_br = dt.astimezone(ZoneInfo("America/Sao_Paulo"))
        return dt_br.strftime("%d/%m/%Y · %H:%M")
    except (ValueError, TypeError):
        return text


def label_status_rastreamento_melhor_envio(status):
    status = str(status or "").strip().lower()
    if not status:
        return "Aguardando atualização"
    return MELHOR_ENVIO_TRACKING_LABELS.get(
        status,
        status.replace("_", " ").capitalize(),
    )


def formatar_cep_kehai(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return str(value or "")


def formatar_cpf_kehai(value):
    digits = somente_digitos(value)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return str(value or "")


def mascarar_cpf_kehai(value):
    digits = somente_digitos(value)
    if len(digits) == 11:
        return f"***.***.***-{digits[-2:]}"
    return "—"


def construir_timeline_pedido_kehai(contexto):
    status_pagamento = str(contexto.get("status") or "").lower()
    status_logistico = str(contexto.get("me_tracking_status") or "").lower()
    fulfillment = str(contexto.get("fulfillment_status") or "pending").lower()

    pagamento_ok = (
        status_pagamento == "paid"
        or bool(contexto.get("payment_confirmed_at"))
    )

    frete_liberado = bool(
        contexto.get("me_released_at")
        or contexto.get("me_purchased_at")
        or status_logistico in {
            "released", "generated", "received", "posted", "delivered",
            "undelivered", "paused", "suspended",
        }
    )

    etiqueta_pronta = bool(
        contexto.get("me_generated_at")
        or contexto.get("me_label_url")
        or str(contexto.get("me_shipment_status") or "").lower()
           in {"generated", "label_ready"}
        or status_logistico in {
            "generated", "received", "posted", "delivered",
            "undelivered", "paused", "suspended",
        }
    )

    postado = bool(
        contexto.get("shipped_at")
        or fulfillment in {"shipped", "delivered"}
        or status_logistico in {
            "posted", "received", "delivered",
            "undelivered", "paused", "suspended",
        }
    )

    entregue = bool(
        contexto.get("delivered_at")
        or fulfillment == "delivered"
        or status_logistico == "delivered"
    )

    # "Em trânsito" é uma camada de apresentação: inicia após a postagem
    # e permanece ativa até a entrega, mesmo que a API use "posted".
    em_transito = postado

    if entregue:
        current_index = 6
    elif em_transito:
        current_index = 5
    elif etiqueta_pronta:
        current_index = 3
    elif frete_liberado:
        current_index = 2
    elif pagamento_ok:
        current_index = 1
    else:
        current_index = 0

    raw_steps = [
        {
            "key": "payment",
            "label": "Pagamento confirmado",
            "description": "Pagamento aprovado e pedido liberado.",
            "date": contexto.get("payment_confirmed_at") or (
                contexto.get("created_at") if pagamento_ok else None
            ),
        },
        {
            "key": "released",
            "label": "Frete liberado",
            "description": "Frete comprado e liberado para geração.",
            "date": contexto.get("me_released_at") or contexto.get("me_purchased_at"),
        },
        {
            "key": "label",
            "label": "Etiqueta pronta",
            "description": "Etiqueta gerada e disponível para impressão.",
            "date": contexto.get("me_generated_at") or contexto.get("me_printed_at"),
        },
        {
            "key": "posted",
            "label": "Postado",
            "description": "Objeto entregue à rede de transporte.",
            "date": contexto.get("shipped_at"),
        },
        {
            "key": "transit",
            "label": "Em trânsito",
            "description": "Encomenda a caminho do destinatário.",
            "date": contexto.get("shipped_at"),
        },
        {
            "key": "delivered",
            "label": "Entregue",
            "description": "Entrega confirmada ao destinatário.",
            "date": contexto.get("delivered_at"),
        },
    ]

    steps = []
    for index, item in enumerate(raw_steps, start=1):
        state = "pending"
        if current_index:
            if index < current_index:
                state = "done"
            elif index == current_index:
                state = "current"
        if entregue and index == 6:
            state = "done-current"

        item = dict(item)
        item["number"] = index
        item["state"] = state
        item["date_label"] = formatar_data_hora_br(item.get("date"))
        steps.append(item)

    current_label = (
        raw_steps[current_index - 1]["label"]
        if current_index
        else "Aguardando pagamento"
    )

    if status_logistico in {"undelivered", "paused", "suspended"}:
        current_label = label_status_rastreamento_melhor_envio(status_logistico)
    elif status_logistico in {"cancelled", "canceled"} or fulfillment == "cancelled":
        current_label = "Envio cancelado"

    return steps, current_label


def contexto_admin_pedido_kehai(pedido):
    contexto = contexto_pedido_kehai(pedido) or {}
    if (
        contexto.get("status") != "paid"
        and (contexto.get("fulfillment_status") or "pending") == "pending"
    ):
        contexto["fulfillment_label"] = "Aguardando pagamento"
    else:
        contexto["fulfillment_label"] = FULFILLMENT_LABELS.get(
            contexto.get("fulfillment_status") or "pending",
            contexto.get("fulfillment_status") or "—",
        )
    contexto["postal_code_formatado"] = formatar_cep_kehai(
        contexto.get("postal_code")
    )
    contexto["customer_document_formatado"] = formatar_cpf_kehai(
        contexto.get("customer_document")
    )
    contexto["customer_document_masked"] = mascarar_cpf_kehai(
        contexto.get("customer_document")
    )
    contexto["sender_configured"] = all([
        MELHOR_ENVIO_FROM_NAME,
        MELHOR_ENVIO_FROM_EMAIL,
        MELHOR_ENVIO_FROM_PHONE,
        MELHOR_ENVIO_FROM_COMPANY_DOCUMENT,
        MELHOR_ENVIO_FROM_ADDRESS,
        MELHOR_ENVIO_FROM_NUMBER,
        MELHOR_ENVIO_FROM_DISTRICT,
        MELHOR_ENVIO_FROM_CITY,
        MELHOR_ENVIO_FROM_POSTAL_CODE,
        MELHOR_ENVIO_FROM_STATE_ABBR,
    ])
    contexto["tracking_status_label"] = label_status_rastreamento_melhor_envio(
        contexto.get("me_tracking_status")
    )
    contexto["tracking_is_problem"] = (
        str(contexto.get("me_tracking_status") or "").lower()
        in {"undelivered", "paused", "suspended", "cancelled", "canceled"}
    )
    contexto["tracking_is_delivered"] = (
        str(contexto.get("me_tracking_status") or "").lower() == "delivered"
    )
    contexto["tracking_event_label"] = label_evento_melhor_envio(
        contexto.get("me_webhook_event")
    )
    contexto["tracking_source_label"] = label_origem_rastreamento(
        contexto.get("me_tracking_source")
    )
    contexto["tracking_event_at_label"] = formatar_data_hora_br(
        contexto.get("me_tracking_event_at")
    )
    contexto["tracking_updated_at_label"] = formatar_data_hora_br(
        contexto.get("me_tracking_updated_at")
    )
    contexto["payment_confirmed_at_label"] = formatar_data_hora_br(
        contexto.get("payment_confirmed_at")
    )

    timeline, timeline_current_label = construir_timeline_pedido_kehai(contexto)
    contexto["timeline"] = timeline
    contexto["timeline_current_label"] = timeline_current_label

    contexto["email_configured"] = email_kehai_configurado()
    contexto["email_confirmation_sent_label"] = formatar_data_hora_br(
        contexto.get("email_confirmation_sent_at")
    )
    contexto["email_shipping_sent_label"] = formatar_data_hora_br(
        contexto.get("email_shipping_sent_at")
    )
    contexto["email_delivery_sent_label"] = formatar_data_hora_br(
        contexto.get("email_delivery_sent_at")
    )

    return contexto


def listar_pedidos_kehai(status_pagamento="", fulfillment_status=""):
    clauses = []
    values = []

    if status_pagamento:
        clauses.append("status = ?")
        values.append(status_pagamento)

    if fulfillment_status:
        clauses.append("fulfillment_status = ?")
        values.append(fulfillment_status)

    where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    with get_kehai_db() as conn:
        rows = conn.execute(
            "SELECT * FROM kehai_orders"
            + where_sql
            + " ORDER BY id DESC LIMIT 300",
            values,
        ).fetchall()

    return [contexto_admin_pedido_kehai(dict(row)) for row in rows]


def kehai_admin_required(view_function):
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        if session.get("kehai_admin_authenticated") is not True:
            return redirect(url_for("kehai_admin_login"))
        return view_function(*args, **kwargs)
    return wrapped


# =====================================================
# KEHAI - MELHOR ENVIO - ETIQUETA / EXPEDIÇÃO
# =====================================================

def criar_envio_melhor_envio(pedido):
    if pedido.get("status") != "paid":
        raise RuntimeError("O pedido precisa estar pago antes de preparar o envio.")

    if pedido.get("me_shipment_id"):
        return pedido["me_shipment_id"]

    validar_configuracao_remetente_melhor_envio()

    cpf = somente_digitos(pedido.get("customer_document"))
    if len(cpf) != 11:
        raise RuntimeError("Informe o CPF do destinatário antes de preparar o envio.")

    invoice_key = somente_digitos(pedido.get("invoice_key"))
    nfe_valida, nfe_erro = validar_chave_nfe_modelo_55(invoice_key)
    if not nfe_valida:
        raise RuntimeError(nfe_erro)

    company_document = somente_digitos(MELHOR_ENVIO_FROM_COMPANY_DOCUMENT)
    if len(company_document) != 14:
        raise RuntimeError("O CNPJ do remetente deve conter 14 dígitos.")

    product = KEHAI_PRODUCTS["physical"]

    from_data = {
        "name": MELHOR_ENVIO_FROM_NAME,
        "email": MELHOR_ENVIO_FROM_EMAIL,
        "phone": somente_digitos(MELHOR_ENVIO_FROM_PHONE),
        "company_document": company_document,
        "address": MELHOR_ENVIO_FROM_ADDRESS,
        "complement": MELHOR_ENVIO_FROM_COMPLEMENT,
        "number": MELHOR_ENVIO_FROM_NUMBER,
        "district": MELHOR_ENVIO_FROM_DISTRICT,
        "city": MELHOR_ENVIO_FROM_CITY,
        "postal_code": somente_digitos(MELHOR_ENVIO_FROM_POSTAL_CODE),
        "state_abbr": MELHOR_ENVIO_FROM_STATE_ABBR,
    }

    if MELHOR_ENVIO_FROM_ECONOMIC_ACTIVITY_CODE:
        from_data["economic_activity_code"] = somente_digitos(
            MELHOR_ENVIO_FROM_ECONOMIC_ACTIVITY_CODE
        )

    payload = {
        "service": int(str(pedido["shipping_service_id"])),
        "from": from_data,
        "to": {
            "name": pedido["customer_name"],
            "email": pedido["customer_email"],
            "phone": somente_digitos(pedido["customer_phone"]),
            "document": cpf,
            "address": pedido["street"],
            "complement": pedido.get("complement") or "",
            "number": pedido["address_number"],
            "district": pedido["district"],
            "city": pedido["city"],
            "postal_code": somente_digitos(pedido["postal_code"]),
            "country_id": "BR",
            "state_abbr": pedido["state"],
        },
        "products": [
            {
                "name": product["title"],
                "quantity": int(pedido.get("quantity") or 1),
                "unitary_value": centavos_para_reais(
                    pedido.get("unit_price_cents") or product["unit_price_cents"]
                ),
            }
        ],
        "volumes": [
            {
                "height": product["height"],
                "width": product["width"],
                "length": product["length"],
                "weight": product["weight"],
            }
        ],
        "options": {
            "platform": "KEHAI - Loja Oficial",
            "reminder": pedido["order_number"],
            "insurance_value": centavos_para_reais(
                pedido.get("subtotal_cents") or product["unit_price_cents"]
            ),
            "receipt": False,
            "own_hand": False,
            "reverse": False,
            "invoice": {
                "key": invoice_key,
            },
            "tags": [
                {
                    "tag": pedido["order_number"],
                    "url": url_for(
                        "kehai_admin_order_detail",
                        order_number=pedido["order_number"],
                        _external=True,
                        _scheme="https",
                    ),
                }
            ],
        },
    }

    response = melhor_envio_request(
        "POST",
        "/api/v2/me/cart",
        json_payload=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        message = response.text[:1200]
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_last_error=f"Carrinho HTTP {response.status_code}: {message}",
        )
        raise RuntimeError(
            f"Melhor Envio recusou a criação do envio (HTTP {response.status_code})."
        )

    data = response.json()
    shipment_id = (
        data.get("id")
        or data.get("order", {}).get("id")
        or data.get("data", {}).get("id")
    )

    if not shipment_id:
        raise RuntimeError("O Melhor Envio não retornou o ID da etiqueta.")

    atualizar_pedido_kehai(
        pedido["order_number"],
        me_shipment_id=str(shipment_id),
        me_shipment_status="cart",
        me_cart_created_at=agora_iso(),
        me_last_error=None,
    )

    return str(shipment_id)


def comprar_envio_melhor_envio(pedido):
    shipment_id = pedido.get("me_shipment_id")
    if not shipment_id:
        raise RuntimeError("Prepare o envio no carrinho antes de comprar o frete.")

    if pedido.get("me_purchased_at"):
        return True

    response = melhor_envio_request(
        "POST",
        "/api/v2/me/shipment/checkout",
        json_payload={"orders": [str(shipment_id)]},
        timeout=30,
    )

    if not response.ok:
        message = response.text[:1200]
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_last_error=f"Checkout HTTP {response.status_code}: {message}",
        )
        raise RuntimeError(
            f"Não foi possível comprar o frete no Melhor Envio (HTTP {response.status_code})."
        )

    atualizar_pedido_kehai(
        pedido["order_number"],
        me_shipment_status="purchased",
        me_purchased_at=agora_iso(),
        me_last_error=None,
    )
    return True


def gerar_etiqueta_melhor_envio(pedido):
    shipment_id = pedido.get("me_shipment_id")
    if not shipment_id or not pedido.get("me_purchased_at"):
        raise RuntimeError("Compre o frete antes de gerar a etiqueta.")

    if pedido.get("me_generated_at"):
        return True

    response = melhor_envio_request(
        "POST",
        "/api/v2/me/shipment/generate",
        json_payload={"orders": [str(shipment_id)]},
        timeout=30,
    )

    if not response.ok:
        message = response.text[:1200]
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_last_error=f"Geração HTTP {response.status_code}: {message}",
        )
        raise RuntimeError(
            f"Não foi possível gerar a etiqueta (HTTP {response.status_code})."
        )

    atualizar_pedido_kehai(
        pedido["order_number"],
        me_shipment_status="generated",
        me_generated_at=agora_iso(),
        me_last_error=None,
    )
    return True


def obter_link_etiqueta_melhor_envio(pedido):
    shipment_id = pedido.get("me_shipment_id")
    if not shipment_id or not pedido.get("me_generated_at"):
        raise RuntimeError("Gere a etiqueta antes de solicitar a impressão.")

    response = melhor_envio_request(
        "POST",
        "/api/v2/me/shipment/print",
        json_payload={
            "mode": "public",
            "orders": [str(shipment_id)],
        },
        timeout=30,
    )

    if not response.ok:
        message = response.text[:1200]
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_last_error=f"Impressão HTTP {response.status_code}: {message}",
        )
        raise RuntimeError(
            f"Não foi possível obter o link da etiqueta (HTTP {response.status_code})."
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    label_url = None
    if isinstance(data, dict):
        label_url = (
            data.get("url")
            or data.get("link")
            or (data.get("data") or {}).get("url")
        )

    if not label_url:
        raw_text = (response.text or "").strip().strip('"')
        if raw_text.startswith("http://") or raw_text.startswith("https://"):
            label_url = raw_text

    if not label_url:
        raise RuntimeError("O Melhor Envio não retornou o link de impressão.")

    atualizar_pedido_kehai(
        pedido["order_number"],
        me_label_url=label_url,
        me_shipment_status="label_ready",
        me_printed_at=agora_iso(),
        fulfillment_status="ready_to_ship",
        fulfillment_updated_at=agora_iso(),
        me_last_error=None,
    )

    return label_url


# =====================================================
# KEHAI - MELHOR ENVIO - RASTREAMENTO
# =====================================================

def _extrair_item_rastreamento_melhor_envio(payload, shipment_id):
    """
    A API já retornou formatos diferentes ao longo do tempo.
    Este extrator aceita resposta direta, lista, chaveada pelo ID
    ou encapsulada em 'data'/'orders'.
    """
    shipment_id = str(shipment_id or "").strip()

    if isinstance(payload, dict):
        if str(payload.get("id") or "").strip() == shipment_id:
            return payload

        keyed = payload.get(shipment_id)
        if isinstance(keyed, dict):
            item = dict(keyed)
            item.setdefault("id", shipment_id)
            return item

        for key in ("data", "orders", "results"):
            if key in payload:
                found = _extrair_item_rastreamento_melhor_envio(
                    payload[key], shipment_id
                )
                if found:
                    return found

        # Algumas respostas vêm com um único objeto aninhado.
        dict_values = [value for value in payload.values() if isinstance(value, dict)]
        if len(dict_values) == 1:
            found = _extrair_item_rastreamento_melhor_envio(
                dict_values[0], shipment_id
            )
            if found:
                return found

    if isinstance(payload, list):
        for item in payload:
            found = _extrair_item_rastreamento_melhor_envio(item, shipment_id)
            if found:
                return found

    return None


def _data_evento_rastreamento_melhor_envio(data):
    for key in (
        "delivered_at",
        "posted_at",
        "generated_at",
        "paid_at",
        "created_at",
        "updated_at",
    ):
        value = data.get(key) if isinstance(data, dict) else None
        if value:
            return str(value)
    return agora_iso()


def aplicar_rastreamento_melhor_envio(
    pedido,
    data,
    *,
    source="api",
    event=None,
):
    if not pedido or not isinstance(data, dict):
        raise RuntimeError("Dados de rastreamento inválidos.")

    shipment_id = str(data.get("id") or pedido.get("me_shipment_id") or "").strip()
    if not shipment_id:
        raise RuntimeError("O rastreamento não informou o ID do envio.")

    if pedido.get("me_shipment_id") and str(pedido["me_shipment_id"]) != shipment_id:
        raise RuntimeError("O retorno do Melhor Envio pertence a outro envio.")

    status = str(data.get("status") or "").strip().lower()
    protocol = str(data.get("protocol") or pedido.get("me_protocol") or "").strip()
    tracking = str(data.get("tracking") or "").strip()
    self_tracking = str(data.get("self_tracking") or "").strip()
    tracking_url = str(data.get("tracking_url") or "").strip()

    # Preferimos o rastreio oficial da transportadora. O self_tracking
    # é usado apenas como fallback quando a transportadora ainda não
    # publicou um código próprio.
    tracking_code = tracking or self_tracking or str(pedido.get("tracking_code") or "").strip()

    event_at = _data_evento_rastreamento_melhor_envio(data)

    fields = {
        "me_protocol": protocol or None,
        "me_tracking_status": status or pedido.get("me_tracking_status"),
        "me_tracking_url": tracking_url or pedido.get("me_tracking_url"),
        "me_tracking_event_at": event_at,
        "me_tracking_updated_at": agora_iso(),
        "me_tracking_source": source,
        "me_webhook_event": str(event or "").strip() or pedido.get("me_webhook_event"),
        "me_tracking_last_error": None,
    }

    if status == "released" and not pedido.get("me_released_at"):
        fields["me_released_at"] = (
            data.get("paid_at") or event_at or agora_iso()
        )

    if status == "generated" and not pedido.get("me_generated_at"):
        fields["me_generated_at"] = (
            data.get("generated_at") or event_at or agora_iso()
        )

    if tracking_code:
        fields["tracking_code"] = tracking_code

    current_fulfillment = str(pedido.get("fulfillment_status") or "pending")

    # Nunca regredimos um pedido já entregue por causa de uma
    # notificação atrasada/cacheada.
    if current_fulfillment != "delivered":
        if status == "delivered":
            fields["fulfillment_status"] = "delivered"
            fields["fulfillment_updated_at"] = agora_iso()
            fields["delivered_at"] = (
                data.get("delivered_at") or pedido.get("delivered_at") or agora_iso()
            )
            if not pedido.get("shipped_at"):
                fields["shipped_at"] = data.get("posted_at") or agora_iso()

        elif status in {"posted", "received", "undelivered", "paused", "suspended"}:
            if current_fulfillment not in {"cancelled"}:
                fields["fulfillment_status"] = "shipped"
                fields["fulfillment_updated_at"] = agora_iso()
                fields["shipped_at"] = (
                    pedido.get("shipped_at")
                    or data.get("posted_at")
                    or event_at
                    or agora_iso()
                )

        elif status in {"cancelled", "canceled"}:
            fields["fulfillment_status"] = "cancelled"
            fields["fulfillment_updated_at"] = agora_iso()

    atualizar_pedido_kehai(pedido["order_number"], **fields)
    pedido_atualizado = buscar_pedido_kehai(pedido["order_number"])

    novo_fulfillment = str(
        pedido_atualizado.get("fulfillment_status") or "pending"
    )

    if (
        novo_fulfillment == "shipped"
        and current_fulfillment != "shipped"
    ):
        tentar_email_kehai(
            pedido_atualizado,
            "shipping",
        )

    if (
        novo_fulfillment == "delivered"
        and current_fulfillment != "delivered"
    ):
        tentar_email_kehai(
            pedido_atualizado,
            "delivery",
        )

    return buscar_pedido_kehai(pedido["order_number"])


def sincronizar_rastreamento_melhor_envio(pedido):
    shipment_id = str(pedido.get("me_shipment_id") or "").strip()
    if not shipment_id:
        raise RuntimeError("O pedido ainda não possui ID de envio do Melhor Envio.")

    response = melhor_envio_request(
        "POST",
        "/api/v2/me/shipment/tracking",
        json_payload={"orders": [shipment_id]},
        timeout=30,
    )

    if not response.ok:
        message = response.text[:1200]
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_tracking_last_error=(
                f"Rastreamento HTTP {response.status_code}: {message}"
            ),
        )
        raise RuntimeError(
            f"Não foi possível consultar o rastreamento (HTTP {response.status_code})."
        )

    try:
        payload = response.json()
    except ValueError:
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_tracking_last_error="O Melhor Envio retornou rastreamento sem JSON válido.",
        )
        raise RuntimeError("Resposta de rastreamento inválida.")

    item = _extrair_item_rastreamento_melhor_envio(payload, shipment_id)
    if not item:
        atualizar_pedido_kehai(
            pedido["order_number"],
            me_tracking_last_error=(
                "A consulta foi aceita, mas não retornou o envio solicitado."
            ),
        )
        raise RuntimeError("O Melhor Envio não retornou o envio solicitado.")

    return aplicar_rastreamento_melhor_envio(
        pedido,
        item,
        source="api",
    )


def validar_assinatura_webhook_melhor_envio(raw_body, received_signature):
    secret = MELHOR_ENVIO_WEBHOOK_SECRET
    if not secret or not received_signature:
        return False

    digest = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).digest()

    expected_base64 = base64.b64encode(digest).decode("ascii")
    expected_hex = digest.hex()
    received = str(received_signature).strip()

    candidates = {
        expected_base64,
        expected_base64.rstrip("="),
        expected_hex,
        f"sha256={expected_hex}",
    }

    return any(
        secrets.compare_digest(received, candidate)
        for candidate in candidates
    )


def localizar_pedido_por_webhook_melhor_envio(data):
    shipment_id = str(data.get("id") or "").strip()
    pedido = buscar_pedido_kehai_por_shipment_id(shipment_id)
    if pedido:
        return pedido

    # Fallback pela tag que já enviamos ao criar a etiqueta.
    for tag_item in data.get("tags") or []:
        if not isinstance(tag_item, dict):
            continue
        tag = str(tag_item.get("tag") or "").strip()
        if tag.startswith("KEHAI-"):
            pedido = buscar_pedido_kehai(tag)
            if pedido:
                return pedido

    return None


# =====================================================
# KEHAI - PAINEL ADMINISTRATIVO / PÓS-VENDA
# =====================================================

@app.route("/kehai/admin/login", methods=["GET", "POST"])
def kehai_admin_login():
    if session.get("kehai_admin_authenticated") is True:
        return redirect(url_for("kehai_admin_orders"))

    error = None

    if request.method == "POST":
        password = str(request.form.get("password") or "")

        if not KEHAI_ADMIN_PASSWORD:
            error = (
                "A senha administrativa ainda não foi configurada no servidor."
            )
        elif secrets.compare_digest(password, KEHAI_ADMIN_PASSWORD):
            session.clear()
            session.permanent = True
            session["kehai_admin_authenticated"] = True
            return redirect(url_for("kehai_admin_orders"))
        else:
            error = "Senha inválida."

    return render_template(
        "kehai_admin_login.html",
        error=error,
        admin_configured=bool(KEHAI_ADMIN_PASSWORD),
    )


@app.route("/kehai/admin/logout", methods=["POST"])
@kehai_admin_required
def kehai_admin_logout():
    session.pop("kehai_admin_authenticated", None)
    return redirect(url_for("kehai_admin_login"))


@app.route("/kehai/admin/pedidos")
@kehai_admin_required
def kehai_admin_orders():
    payment_filter = str(request.args.get("payment") or "").strip()
    fulfillment_filter = str(request.args.get("fulfillment") or "").strip()

    pedidos = listar_pedidos_kehai(
        status_pagamento=payment_filter,
        fulfillment_status=fulfillment_filter,
    )

    all_orders = listar_pedidos_kehai()
    counts = {
        "paid": sum(1 for p in all_orders if p.get("status") == "paid"),
        "pending": sum(
            1 for p in all_orders
            if p.get("status") == "paid"
            and (p.get("fulfillment_status") or "pending") == "pending"
        ),
        "preparing": sum(
            1 for p in all_orders
            if (p.get("fulfillment_status") or "pending") == "preparing"
        ),
        "ready_to_ship": sum(
            1 for p in all_orders
            if (p.get("fulfillment_status") or "pending") == "ready_to_ship"
        ),
        "shipped": sum(
            1 for p in all_orders
            if (p.get("fulfillment_status") or "pending") == "shipped"
        ),
        "delivered": sum(
            1 for p in all_orders
            if (p.get("fulfillment_status") or "pending") == "delivered"
        ),
    }

    return render_template(
        "kehai_admin_orders.html",
        pedidos=pedidos,
        counts=counts,
        payment_filter=payment_filter,
        fulfillment_filter=fulfillment_filter,
        fulfillment_labels=FULFILLMENT_LABELS,
    )


@app.route("/kehai/admin/pedidos/<order_number>")
@kehai_admin_required
def kehai_admin_order_detail(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    return render_template(
        "kehai_admin_order_detail.html",
        pedido=contexto_admin_pedido_kehai(pedido),
        fulfillment_labels=FULFILLMENT_LABELS,
    )



@app.route(
    "/kehai/admin/pedidos/<order_number>/email/<tipo>",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_order_email(order_number, tipo):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    if tipo not in {"confirmation", "shipping", "delivery"}:
        abort(404)

    result = enviar_email_transacional_kehai(
        pedido,
        tipo,
        force=True,
    )

    if result.get("ok"):
        flash("E-mail enviado com sucesso.", "success")
    else:
        flash(
            "Não foi possível enviar o e-mail: "
            + str(result.get("error") or result.get("reason") or "erro desconhecido"),
            "error",
        )

    return redirect(
        url_for(
            "kehai_admin_order_detail",
            order_number=order_number,
        )
    )


@app.route(
    "/kehai/admin/pedidos/<order_number>/operacao",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_order_operation(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    target_status = str(request.form.get("fulfillment_status") or "").strip()
    internal_notes = str(request.form.get("internal_notes") or "").strip()

    if target_status not in FULFILLMENT_LABELS:
        abort(400)

    if pedido.get("status") != "paid" and target_status not in {"pending", "cancelled"}:
        return (
            "Este pedido ainda não possui pagamento confirmado.",
            409,
        )

    fields = {
        "fulfillment_status": target_status,
        "fulfillment_updated_at": agora_iso(),
        # O rastreamento agora é gerenciado pelo Melhor Envio.
        # Não sobrescrevemos tracking_code pelo formulário manual.
        "internal_notes": internal_notes or None,
    }

    if target_status == "shipped":
        fields["shipped_at"] = pedido.get("shipped_at") or agora_iso()

    if target_status == "delivered":
        fields["delivered_at"] = pedido.get("delivered_at") or agora_iso()

    atualizar_pedido_kehai(order_number, **fields)

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/fiscal",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_order_fiscal(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    customer_document = somente_digitos(
        request.form.get("customer_document") or ""
    )
    invoice_key = somente_digitos(
        request.form.get("invoice_key") or ""
    )

    if len(customer_document) != 11:
        flash("Informe um CPF válido com 11 dígitos.", "error")
        return redirect(url_for("kehai_admin_order_detail", order_number=order_number))

    nfe_valida, nfe_erro = validar_chave_nfe_modelo_55(invoice_key)
    if not nfe_valida:
        flash(nfe_erro, "error")
        return redirect(url_for("kehai_admin_order_detail", order_number=order_number))

    atualizar_pedido_kehai(
        order_number,
        customer_document=customer_document,
        invoice_key=invoice_key,
        me_last_error=None,
    )

    flash("Dados fiscais do envio salvos.", "success")
    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/melhor-envio/preparar",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_me_prepare(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    try:
        criar_envio_melhor_envio(pedido)
        flash("Envio inserido no carrinho do Melhor Envio.", "success")
    except Exception as erro:
        print(f"[MELHOR ENVIO ADMIN] Preparar: {erro}")
        flash(str(erro), "error")

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/melhor-envio/comprar",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_me_purchase(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    try:
        comprar_envio_melhor_envio(pedido)
        flash("Frete comprado no Melhor Envio.", "success")
    except Exception as erro:
        print(f"[MELHOR ENVIO ADMIN] Comprar: {erro}")
        flash(str(erro), "error")

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/melhor-envio/gerar",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_me_generate(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    try:
        gerar_etiqueta_melhor_envio(pedido)
        flash(
            "Etiqueta gerada. Aguarde alguns segundos antes de solicitar a impressão.",
            "success",
        )
    except Exception as erro:
        print(f"[MELHOR ENVIO ADMIN] Gerar: {erro}")
        flash(str(erro), "error")

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/melhor-envio/imprimir",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_me_print(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    try:
        obter_link_etiqueta_melhor_envio(pedido)
        flash("Link de impressão da etiqueta obtido.", "success")
    except Exception as erro:
        print(f"[MELHOR ENVIO ADMIN] Imprimir: {erro}")
        flash(str(erro), "error")

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


@app.route(
    "/kehai/admin/pedidos/<order_number>/melhor-envio/rastreamento",
    methods=["POST"],
)
@kehai_admin_required
def kehai_admin_me_tracking(order_number):
    pedido = buscar_pedido_kehai(order_number)
    if not pedido:
        abort(404)

    try:
        atualizado = sincronizar_rastreamento_melhor_envio(pedido)
        tracking_label = label_status_rastreamento_melhor_envio(
            atualizado.get("me_tracking_status")
        )
        tracking_code = atualizado.get("tracking_code")
        if tracking_code:
            flash(
                f"Rastreamento atualizado: {tracking_label} · {tracking_code}.",
                "success",
            )
        else:
            flash(
                f"Rastreamento atualizado: {tracking_label}. "
                "A transportadora ainda não informou o código de rastreio.",
                "success",
            )
    except Exception as erro:
        print(f"[MELHOR ENVIO ADMIN] Rastreio: {erro}")
        flash(str(erro), "error")

    return redirect(url_for("kehai_admin_order_detail", order_number=order_number))


# =====================================================
# KEHAI - WEBHOOK MELHOR ENVIO
# =====================================================

@app.route("/api/kehai/melhor-envio/webhook", methods=["GET", "POST"])
def kehai_melhor_envio_webhook():
    # GET serve apenas como health-check da URL pública.
    if request.method == "GET":
        return jsonify({
            "ok": True,
            "service": "kehai-melhor-envio-webhook",
            "signature_configured": bool(MELHOR_ENVIO_WEBHOOK_SECRET),
        })

    raw_body = request.get_data(cache=True)
    received_signature = request.headers.get("X-ME-Signature", "")

    if not MELHOR_ENVIO_WEBHOOK_SECRET:
        print("[MELHOR ENVIO WEBHOOK] Secret do aplicativo não configurado.")
        return jsonify({"received": False, "error": "Webhook não configurado."}), 500

    if not validar_assinatura_webhook_melhor_envio(
        raw_body,
        received_signature,
    ):
        print("[MELHOR ENVIO WEBHOOK] Assinatura inválida.")
        return jsonify({"received": False, "error": "Assinatura inválida."}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"received": False, "error": "JSON inválido."}), 400

    event = str(payload.get("event") or "").strip()
    data = payload.get("data")

    if not event.startswith("order.") or not isinstance(data, dict):
        # Eventos desconhecidos são reconhecidos com 200 para evitar
        # retentativas desnecessárias do provedor.
        return jsonify({"received": True, "ignored": True}), 200

    pedido = localizar_pedido_por_webhook_melhor_envio(data)
    if not pedido:
        print(
            "[MELHOR ENVIO WEBHOOK] Pedido não localizado para shipment=",
            data.get("id"),
        )
        return jsonify({"received": True, "matched": False}), 200

    try:
        atualizado = aplicar_rastreamento_melhor_envio(
            pedido,
            data,
            source="webhook",
            event=event,
        )
    except Exception as erro:
        print(f"[MELHOR ENVIO WEBHOOK] Falha ao processar: {erro}")
        # Retornamos erro para permitir as retentativas oficiais.
        return jsonify({"received": False, "error": "processing_failed"}), 500

    return jsonify({
        "received": True,
        "matched": True,
        "order": atualizado.get("order_number"),
        "status": atualizado.get("me_tracking_status"),
    }), 200


# =====================================================
# KEHAI EBOOK - PROCESSAMENTO DO WEBHOOK
# =====================================================

def processar_pagamento_ebook_webhook(
    *,
    external_reference,
    payment_id,
    status,
    transaction_amount,
    total_paid_amount,
    merchant_total_amount,
    merchant_paid_amount,
    merchant_order_status,
    pagamento,
):

    pedido = buscar_pedido_ebook_kehai(
        external_reference
    )

    if not pedido:
        return False


    def em_centavos(valor):

        if valor is None:
            return None

        try:

            return reais_para_centavos(
                valor
            )

        except (
            ValueError,
            TypeError,
        ):

            return None


    transaction_cents = em_centavos(
        transaction_amount
    )

    total_paid_cents = em_centavos(
        total_paid_amount
    )

    merchant_total_cents = em_centavos(
        merchant_total_amount
    )

    merchant_paid_cents = em_centavos(
        merchant_paid_amount
    )


    order_status = (
        pedido["status"]
    )


    # ---------------------------------------------
    # PAGAMENTO APROVADO
    # ---------------------------------------------

    if status == "approved":

        esperado = (
            pedido["total_cents"]
        )


        checks = [

            transaction_cents
            ==
            esperado,

            (
                total_paid_cents
                is None

                or

                total_paid_cents
                ==
                esperado
            ),

            (
                merchant_total_cents
                is None

                or

                merchant_total_cents
                ==
                esperado
            ),

            (
                merchant_paid_cents
                is None

                or

                merchant_paid_cents
                ==
                esperado
            ),

            merchant_order_status
            in {
                None,
                "paid",
            },

        ]


        order_status = (

            "paid"

            if all(checks)

            else

            "payment_amount_mismatch"

        )


        if (
            order_status
            !=
            "paid"
        ):

            print(

                "[KEHAI EBOOK WEBHOOK] "
                "Falha na validação financeira. "

                f"esperado_cents={esperado} "

                f"transaction_cents="
                f"{transaction_cents} "

                f"total_paid_cents="
                f"{total_paid_cents} "

                f"merchant_total_cents="
                f"{merchant_total_cents} "

                f"merchant_paid_cents="
                f"{merchant_paid_cents}"

            )


    # ---------------------------------------------
    # PAGAMENTO PENDENTE
    # ---------------------------------------------

    elif status in {

        "pending",
        "in_process",
        "in_mediation",

    }:

        if (
            pedido["status"]
            !=
            "paid"
        ):

            order_status = (
                "payment_pending"
            )


    # ---------------------------------------------
    # PAGAMENTO RECUSADO
    # ---------------------------------------------

    elif status in {

        "rejected",
        "cancelled",

    }:

        if (
            pedido["status"]
            !=
            "paid"
        ):

            order_status = (
                "payment_failed"
            )


    # ---------------------------------------------
    # ESTORNO / CHARGEBACK
    # ---------------------------------------------

    elif status in {

        "refunded",
        "charged_back",

    }:

        order_status = status


    payment_confirmed_at = (
        pedido.get(
            "payment_confirmed_at"
        )
    )


    if (

        order_status
        ==
        "paid"

        and

        not payment_confirmed_at

    ):

        payment_confirmed_at = (

            pagamento.get(
                "date_approved"
            )

            or

            pagamento.get(
                "date_last_updated"
            )

            or

            agora_iso()

        )


    atualizar_pedido_ebook_kehai(

        pedido[
            "order_number"
        ],

        status=
            order_status,

        mp_payment_id=
            str(payment_id),

        mp_payment_status=
            status,

        payment_confirmed_at=
            payment_confirmed_at,

    )


    print(

        "[KEHAI EBOOK WEBHOOK] "

        f"Pedido "
        f"{pedido['order_number']} "

        f"atualizado para "
        f"{order_status}"

    )


    return True

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


            transaction_amount = pagamento.get(
                "transaction_amount"
            )


            transaction_details = (
                pagamento.get("transaction_details")
                or {}
            )


            total_paid_amount = transaction_details.get(
                "total_paid_amount"
            )


            merchant_order_id = (
                (pagamento.get("order") or {}).get("id")
            )


            merchant_order = {}

            if merchant_order_id:
                try:
                    merchant_order_response = requests.get(
                        (
                            "https://api.mercadopago.com/"
                            f"merchant_orders/{merchant_order_id}"
                        ),
                        headers={
                            "Authorization":
                                f"Bearer {MERCADO_PAGO_ACCESS_TOKEN}",
                            "Accept": "application/json",
                        },
                        timeout=20,
                    )

                    if merchant_order_response.ok:
                        merchant_order = (
                            merchant_order_response.json()
                        )
                    else:
                        print(
                            "[MERCADO PAGO WEBHOOK] "
                            "Não foi possível consultar Merchant Order. "
                            f"HTTP {merchant_order_response.status_code}"
                        )

                except Exception as erro_merchant_order:
                    print(
                        "[MERCADO PAGO WEBHOOK] "
                        "Erro ao consultar Merchant Order: "
                        f"{erro_merchant_order}"
                    )


            merchant_external_reference = (
                merchant_order.get("external_reference")
            )

            if merchant_external_reference:
                external_reference = (
                    merchant_external_reference
                )


            merchant_paid_amount = merchant_order.get(
                "paid_amount"
            )


            merchant_total_amount = merchant_order.get(
                "total_amount"
            )


            merchant_shipping_cost = merchant_order.get(
                "shipping_cost"
            )


            merchant_order_status = merchant_order.get(
                "order_status"
            )


            merchant_status = merchant_order.get(
                "status"
            )


            print(
                "[MERCADO PAGO WEBHOOK] "
                f"payment_id={data_id} "
                f"status={status} "
                f"external_reference={external_reference} "
                f"transaction_amount={transaction_amount} "
                f"total_paid_amount={total_paid_amount} "
                f"merchant_order_id={merchant_order_id} "
                f"merchant_status={merchant_status} "
                f"merchant_order_status={merchant_order_status} "
                f"merchant_total_amount={merchant_total_amount} "
                f"merchant_paid_amount={merchant_paid_amount} "
                f"merchant_shipping_cost={merchant_shipping_cost}"
            )

            pedido_ebook_processado = (
                processar_pagamento_ebook_webhook(

                    external_reference=
                        external_reference,

                    payment_id=
                        data_id,

                    status=
                        status,

                    transaction_amount=
                        transaction_amount,

                    total_paid_amount=
                        total_paid_amount,

                    merchant_total_amount=
                        merchant_total_amount,

                    merchant_paid_amount=
                        merchant_paid_amount,

                    merchant_order_status=
                        merchant_order_status,

                    pagamento=
                        pagamento,

                )
            )


            if pedido_ebook_processado:

                return jsonify({
                    "received": True
                }), 200

            pedido = buscar_pedido_kehai(external_reference)

            if pedido:
                # -------------------------------------------------
                # 5. Validar os valores do pedido
                # -------------------------------------------------
                #
                # No Checkout Pro com frete em shipments.cost, os
                # valores observados e confirmados no Mercado Pago são:
                #
                # transaction_amount                  = subtotal do produto
                # Merchant Order total_amount         = subtotal do produto
                # Merchant Order paid_amount          = subtotal do produto
                # Merchant Order shipping_cost        = frete
                # transaction_details.total_paid_amount = produto + frete
                #
                # Portanto, o valor total efetivamente desembolsado pelo
                # comprador é total_paid_amount, e não paid_amount da
                # Merchant Order.

                def _valor_mp_em_centavos(valor):
                    if valor is None:
                        return None

                    try:
                        return reais_para_centavos(valor)
                    except (ValueError, TypeError):
                        return None


                transaction_amount_cents = (
                    _valor_mp_em_centavos(transaction_amount)
                )

                total_paid_amount_cents = (
                    _valor_mp_em_centavos(total_paid_amount)
                )

                merchant_total_cents = (
                    _valor_mp_em_centavos(merchant_total_amount)
                )

                merchant_paid_cents = (
                    _valor_mp_em_centavos(merchant_paid_amount)
                )

                merchant_shipping_cents = (
                    _valor_mp_em_centavos(merchant_shipping_cost)
                )


                order_status = pedido["status"]

                if status == "approved":
                    # Validação principal: o comprador pagou exatamente
                    # subtotal + frete registrados no nosso pedido.
                    total_pago_confere = (
                        total_paid_amount_cents
                        == pedido["total_cents"]
                    )

                    # Valida também os componentes individualmente.
                    subtotal_payment_confere = (
                        transaction_amount_cents is None
                        or transaction_amount_cents
                        == pedido["subtotal_cents"]
                    )

                    subtotal_merchant_total_confere = (
                        merchant_total_cents is None
                        or merchant_total_cents
                        == pedido["subtotal_cents"]
                    )

                    subtotal_merchant_paid_confere = (
                        merchant_paid_cents is None
                        or merchant_paid_cents
                        == pedido["subtotal_cents"]
                    )

                    frete_confere = (
                        merchant_shipping_cents is None
                        or merchant_shipping_cents
                        == pedido["shipping_price_cents"]
                    )

                    merchant_order_pago = (
                        merchant_order_status in {None, "paid"}
                    )

                    if all([
                        total_pago_confere,
                        subtotal_payment_confere,
                        subtotal_merchant_total_confere,
                        subtotal_merchant_paid_confere,
                        frete_confere,
                        merchant_order_pago,
                    ]):
                        order_status = "paid"
                    else:
                        order_status = "payment_amount_mismatch"

                        print(
                            "[MERCADO PAGO WEBHOOK] "
                            "Falha na validação financeira do pedido. "
                            f"esperado_subtotal_cents={pedido['subtotal_cents']} "
                            f"esperado_frete_cents={pedido['shipping_price_cents']} "
                            f"esperado_total_cents={pedido['total_cents']} "
                            f"transaction_amount_cents={transaction_amount_cents} "
                            f"total_paid_amount_cents={total_paid_amount_cents} "
                            f"merchant_total_cents={merchant_total_cents} "
                            f"merchant_paid_cents={merchant_paid_cents} "
                            f"merchant_shipping_cents={merchant_shipping_cents} "
                            f"merchant_order_status={merchant_order_status}"
                        )

                elif status in {"pending", "in_process", "in_mediation"}:
                    if pedido["status"] != "paid":
                        order_status = "payment_pending"

                elif status in {"rejected", "cancelled"}:
                    if pedido["status"] != "paid":
                        order_status = "payment_failed"

                elif status in {"refunded", "charged_back"}:
                    order_status = status

                payment_confirmed_at = pedido.get("payment_confirmed_at")
                if order_status == "paid" and not payment_confirmed_at:
                    payment_confirmed_at = (
                        pagamento.get("date_approved")
                        or pagamento.get("date_last_updated")
                        or agora_iso()
                    )

                status_anterior = pedido.get("status")

                atualizar_pedido_kehai(
                    pedido["order_number"],
                    status=order_status,
                    mp_payment_id=str(data_id),
                    mp_payment_status=status,
                    payment_confirmed_at=payment_confirmed_at,
                )

                if order_status == "paid" and status_anterior != "paid":
                    pedido_atualizado = buscar_pedido_kehai(
                        pedido["order_number"]
                    )
                    tentar_email_kehai(
                        pedido_atualizado,
                        "confirmation",
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
# KEHAI EBOOK - SINCRONIZAÇÃO DO RETORNO
# =====================================================

def sincronizar_pagamento_ebook_kehai(
    payment_id,
    expected_order_number=None,
):

    payment_id = str(
        payment_id
        or ""
    ).strip()


    if not payment_id:

        return None


    sdk = get_mercadopago_sdk()


    pagamento_response = (
        sdk
        .payment()
        .get(
            payment_id
        )
    )


    pagamento = (
        pagamento_response.get(
            "response",
            {}
        )
        or {}
    )


    status = pagamento.get(
        "status"
    )


    external_reference = (
        pagamento.get(
            "external_reference"
        )
    )


    # ---------------------------------------------
    # PROTEÇÃO CONTRA PEDIDO DIFERENTE
    # ---------------------------------------------

    if (
        expected_order_number

        and

        str(
            external_reference
            or ""
        )

        !=

        str(
            expected_order_number
        )
    ):

        print(
            "[KEHAI EBOOK RETORNO] "
            "External reference diferente. "
            f"esperado={expected_order_number} "
            f"recebido={external_reference}"
        )


        return (
            buscar_pedido_ebook_kehai(
                expected_order_number
            )
        )


    pedido = (
        buscar_pedido_ebook_kehai(
            external_reference
        )
    )


    if not pedido:

        return None


    # ---------------------------------------------
    # VALOR
    # ---------------------------------------------

    transaction_amount = (
        pagamento.get(
            "transaction_amount"
        )
    )


    try:

        valor_cents = (
            reais_para_centavos(
                transaction_amount
            )
            if transaction_amount
            is not None
            else None
        )

    except (
        ValueError,
        TypeError,
    ):

        valor_cents = None


    order_status = (
        pedido["status"]
    )


    # ---------------------------------------------
    # STATUS
    # ---------------------------------------------

    if status == "approved":

        if (
            valor_cents
            ==
            pedido["total_cents"]
        ):

            order_status = "paid"

        else:

            order_status = (
                "payment_amount_mismatch"
            )


    elif status in {
        "pending",
        "in_process",
        "in_mediation",
    }:

        if (
            pedido["status"]
            !=
            "paid"
        ):

            order_status = (
                "payment_pending"
            )


    elif status in {
        "rejected",
        "cancelled",
    }:

        if (
            pedido["status"]
            !=
            "paid"
        ):

            order_status = (
                "payment_failed"
            )


    elif status in {
        "refunded",
        "charged_back",
    }:

        order_status = status


    payment_confirmed_at = (
        pedido.get(
            "payment_confirmed_at"
        )
    )


    if (
        order_status == "paid"
        and
        not payment_confirmed_at
    ):

        payment_confirmed_at = (

            pagamento.get(
                "date_approved"
            )

            or

            pagamento.get(
                "date_last_updated"
            )

            or

            agora_iso()

        )


    atualizar_pedido_ebook_kehai(

        pedido[
            "order_number"
        ],

        status=
            order_status,

        mp_payment_id=
            payment_id,

        mp_payment_status=
            status,

        payment_confirmed_at=
            payment_confirmed_at,

    )


    return (
        buscar_pedido_ebook_kehai(
            pedido[
                "order_number"
            ]
        )
    )

# =====================================================
# KEHAI - RETORNOS DO PAGAMENTO
# =====================================================

def _render_kehai_compra_status(page_kind):
    order_number = str(request.args.get("order") or "").strip()
    payment_id = str(
        request.args.get("payment_id")
        or request.args.get("collection_id")
        or ""
    ).strip()

    pedido = buscar_pedido_kehai(order_number) if order_number else None

    # No retorno do Mercado Pago, confirma de forma segura na API.
    # Isso deixa a página correta mesmo se o webhook chegar alguns
    # segundos depois do redirect.
    if payment_id and order_number:
        try:
            pedido_sincronizado = sincronizar_pagamento_kehai(
                payment_id,
                expected_order_number=order_number,
            )
            if pedido_sincronizado:
                pedido = pedido_sincronizado
        except Exception as erro:
            print(
                "[MERCADO PAGO RETORNO] "
                f"Falha ao sincronizar pagamento: {erro}"
            )

    return render_template(
        "kehai_compra_status.html",
        page_kind=page_kind,
        pedido=contexto_pedido_kehai(pedido),
        payment_id=payment_id or None,
    )


@app.route("/kehai/compra/sucesso")
def kehai_compra_sucesso():
    return _render_kehai_compra_status("success")


@app.route("/kehai/compra/pendente")
def kehai_compra_pendente():
    return _render_kehai_compra_status("pending")


@app.route("/kehai/compra/erro")
def kehai_compra_erro():
    return _render_kehai_compra_status("failure")


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

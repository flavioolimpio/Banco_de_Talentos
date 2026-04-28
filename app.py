from __future__ import annotations

import base64
import csv
import hashlib
import secrets
import sqlite3
from datetime import datetime
from io import StringIO
from pathlib import Path

import streamlit as st

try:
    from streamlit_option_menu import option_menu
except ModuleNotFoundError:
    option_menu = None


APP_TITLE = "Banco de Talentos - Polo de Inovação IFG"
LOGO_PATH = Path("logo-ifg-vertical.png")
DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "usuarios.csv"
DB_FILE = DATA_DIR / "banco_talentos.db"
LIME = "#d6f000"
GREEN = "#168241"
INK = "#202124"

USER_FIELDS = [
    "cpf",
    "nome",
    "email",
    "telefone",
    "senha_hash",
    "vinculo",
    "instituicao",
    "lattes",
    "resumo",
    "perfil",
    "data_cadastro",
    "data_nascimento",
    "rg",
    "orgao_emissor",
    "genero",
    "cep",
    "endereco",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
    "nivel_formacao",
    "area_atuacao",
    "linkedin",
    "aceite_lgpd",
]

FORMACAO_NIVEIS = [
    "Técnico",
    "Tecnólogo",
    "Graduação",
    "Especialização",
    "Mestrado",
    "Doutorado",
]

CNPQ_AREAS = [
    "Ciências Exatas e da Terra",
    "Ciências Biológicas",
    "Engenharias",
    "Ciências da Saúde",
    "Ciências Agrárias",
    "Ciências Sociais Aplicadas",
    "Ciências Humanas",
    "Linguística, Letras e Artes",
    "Outra",
]


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="IFG",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css(show_sidebar: bool = False) -> None:
    sidebar_css = """
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none;
        }
    """
    container_css = """
        .block-container {
            max-width: 980px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }
    """

    if show_sidebar:
        sidebar_css = """
            [data-testid="collapsedControl"] {
                display: none;
            }

            [data-testid="stSidebar"] {
                background: #2c363f;
                border-right: 0;
                min-width: 235px !important;
                overflow: hidden;
                width: 235px !important;
            }

            [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding: 1.1rem .85rem .8rem;
                width: 235px;
            }

            [data-testid="stSidebar"] * {
                color: #ffffff;
            }

            [data-testid="stSidebar"] button {
                background: rgba(255, 255, 255, .03) !important;
                border: 0;
                box-shadow: none;
                color: #ffffff !important;
                justify-content: flex-start;
                min-height: 2.6rem;
                text-transform: none;
                width: 100%;
            }

            [data-testid="stSidebar"] button:hover {
                background: rgba(255, 255, 255, .08) !important;
            }

            [data-testid="stAppViewContainer"] {
                overflow: hidden;
            }

            .sidebar-user {
                border-bottom: 1px solid rgba(255,255,255,.10);
                margin: 0 0 1rem;
                padding: .25rem .6rem 1rem;
            }

            .sidebar-user strong {
                display: block;
                font-size: .9rem;
                line-height: 1.15;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .sidebar-user span {
                color: rgba(255,255,255,.78);
                display: block;
                font-size: .82rem;
                font-weight: 700;
                line-height: 1.15;
                margin-top: .15rem;
            }

            .sidebar-nav {
                margin-top: .75rem;
            }

            .sidebar-nav + div [data-testid="stButton"],
            [data-testid="stSidebar"] [data-testid="stButton"] {
                margin: .3rem 0;
            }

            [data-testid="stSidebar"] [data-testid="stButton"] button {
                border-radius: 18px !important;
                font-size: .95rem !important;
                font-weight: 800 !important;
                letter-spacing: 0 !important;
                padding: .35rem .85rem !important;
                text-align: left !important;
                text-transform: none !important;
            }

            .sidebar-footer {
                border-top: 1px solid rgba(255,255,255,.10);
                bottom: .9rem;
                font-size: .78rem;
                font-weight: 800;
                left: 1rem;
                line-height: 1.15;
                padding-top: .85rem;
                position: fixed;
                width: 195px;
            }

            .sidebar-footer .footer-icon {
                border: 2px solid var(--lime);
                border-radius: 6px;
                color: var(--lime);
                display: inline-block;
                font-size: .85rem;
                margin-right: .45rem;
                padding: .1rem .18rem;
                vertical-align: middle;
            }
        """
        container_css = """
            .block-container {
                max-width: none;
                padding: .2rem .75rem .75rem .75rem;
            }
        """

    st.markdown(
        f"""
        <style>
        :root {{
            --ifg-green: {GREEN};
            --ifg-green-dark: #0d5d32;
            --lime: {LIME};
            --ink: {INK};
            --muted: #575757;
            --line: #d8d8d8;
            --soft: #f6faf7;
            --sidebar: #223342;
        }}

        #MainMenu,
        footer,
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {{
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
        }}

        {sidebar_css}
        {container_css}

        .logo-wrap {{
            display: flex;
            justify-content: center;
            margin: 0.25rem 0 2.2rem;
        }}

        .logo-wrap img {{
            max-width: 230px;
            min-width: 180px;
            width: 42vw;
        }}

        .hello {{
            color: var(--ink);
            font-size: clamp(3rem, 7vw, 4.8rem);
            font-weight: 200;
            letter-spacing: 0;
            line-height: 1;
            margin: 0 0 1.45rem;
        }}

        .welcome {{
            color: var(--ink);
            font-size: clamp(1.25rem, 2.6vw, 1.75rem);
            font-weight: 300;
            line-height: 1.25;
            margin-bottom: 1.75rem;
        }}

        .welcome strong {{
            font-weight: 800;
        }}

        .forgot {{
            color: #74b843;
            font-size: 0.82rem;
            font-weight: 800;
            margin: -0.35rem 0 1.65rem;
        }}

        .signup-text {{
            color: #333333;
            font-size: 0.92rem;
            margin-top: 1.1rem;
            text-align: center;
        }}

        .form-shell {{
            background: #ffffff;
            border: 1px solid #e2e5e3;
            border-radius: 8px;
            padding: 1.2rem;
        }}

        .signup-flow {{
            max-width: 890px;
            margin: 0 auto;
            padding-top: 1rem;
        }}

        .signup-edital {{
            background: var(--lime);
            border-radius: 4px;
            box-shadow: 0 3px 7px rgba(0,0,0,.25);
            color: #000000;
            display: block;
            font-size: .92rem;
            font-weight: 900;
            letter-spacing: .06rem;
            margin: 0 auto 2rem;
            max-width: 450px;
            padding: .72rem 1rem;
            text-align: center;
            text-transform: uppercase;
        }}

        .signup-back {{
            color: #111111;
            font-size: 2rem;
            line-height: 1;
            margin: .2rem 0 1.7rem;
        }}

        .signup-prompt {{
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 300;
            margin: 0 0 1.1rem;
        }}

        .category-copy h3 {{
            color: var(--ink);
            font-size: 1.05rem;
            margin: .15rem 0 .25rem;
        }}

        .category-copy p {{
            color: #444444;
            font-size: .92rem;
            margin: 0;
        }}

        .signup-form-title {{
            color: var(--ink);
            font-size: 1.2rem;
            font-weight: 400;
            margin: .5rem 0 1.6rem;
        }}

        .section-title {{
            border-left: 5px solid var(--ifg-green);
            color: var(--ink);
            font-size: 1.15rem;
            font-weight: 800;
            margin: 0.2rem 0 1rem;
            padding-left: 0.65rem;
        }}

        .app-toolbar {{
            align-items: center;
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 5px;
            box-shadow: 0 2px 7px rgba(0, 0, 0, .18);
            display: flex;
            justify-content: space-between;
            margin-bottom: .9rem;
            min-height: 58px;
            padding: 0 2rem;
        }}

        .app-toolbar p {{
            color: var(--ink);
            font-size: 1rem;
            margin: 0;
        }}

        .workspace {{
            align-items: center;
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 5px;
            box-shadow: 0 2px 7px rgba(0, 0, 0, .16);
            display: grid;
            gap: 2rem;
            grid-template-columns: 1.25fr .55fr;
            height: calc(100vh - 104px);
            overflow: hidden;
            padding: 1.25rem 3rem;
        }}

        .hero-art {{
            height: min(360px, calc(100vh - 165px));
            position: relative;
        }}

        .art-blob {{
            background: #f1f1f1;
            border-radius: 42% 58% 50% 50%;
            height: 170px;
            left: 7%;
            position: absolute;
            top: 18%;
            width: 260px;
        }}

        .art-blob.two {{
            height: 165px;
            left: 54%;
            top: 18%;
            width: 260px;
        }}

        .desk {{
            background: #72bd00;
            border-radius: 8px;
            bottom: 52px;
            height: 82px;
            left: 20%;
            position: absolute;
            width: 480px;
        }}

        .screen {{
            background: #eef0f1;
            border: 1px solid #2d3d45;
            border-radius: 5px;
            bottom: 128px;
            height: 162px;
            left: 5%;
            position: absolute;
            width: 220px;
        }}

        .globe {{
            background: #344955;
            border-radius: 50%;
            bottom: 65px;
            height: 190px;
            left: 55%;
            position: absolute;
            width: 190px;
        }}

        .person {{
            background: #6cb600;
            border-radius: 48% 48% 8px 8px;
            bottom: 128px;
            height: 132px;
            left: 44%;
            position: absolute;
            width: 88px;
        }}

        .person::before {{
            background: #f2b28c;
            border-radius: 50%;
            content: "";
            height: 52px;
            left: 18px;
            position: absolute;
            top: -38px;
            width: 52px;
        }}

        .ground {{
            background: #c4cbd0;
            bottom: 60px;
            height: 2px;
            left: 4%;
            position: absolute;
            width: 78%;
        }}

        .action-card {{
            align-items: center;
            background: #ffffff;
            border: 1px solid #e7e7e7;
            border-radius: 4px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, .20);
            color: var(--ink);
            display: flex;
            font-size: 1.05rem;
            font-weight: 700;
            gap: .8rem;
            justify-content: space-between;
            margin: 1.5rem 0;
            min-height: 76px;
            padding: 0 1.7rem;
        }}

        .action-card.primary {{
            background: var(--lime);
            border-color: var(--lime);
        }}

        .placeholder-card {{
            background: #ffffff;
            border: 1px solid #e5e5e5;
            border-radius: 5px;
            box-shadow: 0 2px 7px rgba(0, 0, 0, .14);
            padding: 1.4rem;
        }}

        .registration-page {{
            background: #ffffff;
            border: 1px solid #e8e8e8;
            border-radius: 8px;
            box-shadow: 0 1px 5px rgba(0,0,0,.08);
            min-height: 0;
            padding: 1.35rem 2rem 1.35rem;
        }}

        .registration-title-row {{
            align-items: center;
            display: flex;
            justify-content: space-between;
            margin-bottom: .85rem;
        }}

        .registration-title-row h2 {{
            color: var(--ink);
            font-size: 1.35rem;
            margin: 0;
        }}

        .back-link {{
            color: var(--ink);
            font-size: .86rem;
            font-weight: 800;
            letter-spacing: .08rem;
            text-transform: uppercase;
        }}

        .save-divider {{
            border-top: 1px solid #dfdfdf;
            margin: 1rem 0 .9rem;
        }}

        .registration-page [data-testid="stVerticalBlock"] {{
            gap: .45rem;
        }}

        .registration-tabs {{
            display: grid;
            grid-template-columns: repeat(3, minmax(180px, 360px));
            gap: 1rem;
            margin: .25rem 0 1.4rem;
            max-width: 1120px;
        }}

        .tab-button {{
            align-items: center;
            border-radius: 7px 7px 0 0;
            border-bottom: 2px solid #223342;
            color: #6d6d6d;
            display: flex;
            font-size: .88rem;
            font-weight: 900;
            gap: .55rem;
            height: 48px;
            justify-content: center;
            letter-spacing: .08rem;
            text-transform: uppercase;
            text-decoration: none !important;
        }}

        .tab-button.done {{
            background: var(--lime);
            color: #223342;
        }}

        .tab-button.active {{
            background: #223342;
            color: var(--lime);
        }}

        .tab-button.muted {{
            background: #ffffff;
            border-bottom-color: transparent;
            color: #777777;
        }}

        .tab-control-row {{
            display: none;
        }}

        div.stButton > button,
        div.stFormSubmitButton > button {{
            border: 0;
            border-radius: 5px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.18);
            font-weight: 900;
            letter-spacing: 0.04rem;
            min-height: 3.05rem;
            text-transform: uppercase;
        }}

        div.stButton > button[kind="primary"],
        div.stFormSubmitButton > button[kind="primary"] {{
            background: var(--lime);
            color: #000000;
        }}

        div.stButton > button[kind="secondary"] {{
            background: #ffffff;
            border: 1px solid var(--ifg-green);
            box-shadow: none;
            color: var(--ifg-green-dark);
        }}

        div[data-testid="stTextInput"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stRadio"] label {{
            color: var(--ink);
            font-size: 1rem;
            font-weight: 400;
        }}

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea {{
            border-radius: 2px;
        }}

        @media (max-width: 900px) {{
            .block-container {{
                padding-left: .75rem;
            }}

            .workspace {{
                grid-template-columns: 1fr;
                padding: 1.5rem;
            }}

            .hero-art {{
                min-height: 320px;
            }}
        }}

        @media (max-width: 720px) {{
            .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}

            .logo-wrap {{
                justify-content: flex-start;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, salt, digest = stored_hash.split("$", 2)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return secrets.compare_digest(candidate.hex(), digest)

    return secrets.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored_hash)


def db_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_users_file() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                cpf TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                telefone TEXT DEFAULT '',
                senha_hash TEXT NOT NULL,
                vinculo TEXT DEFAULT '',
                instituicao TEXT DEFAULT '',
                lattes TEXT DEFAULT '',
                resumo TEXT DEFAULT '',
                perfil TEXT DEFAULT 'usuario',
                data_cadastro TEXT DEFAULT '',
                data_nascimento TEXT DEFAULT '',
                rg TEXT DEFAULT '',
                orgao_emissor TEXT DEFAULT '',
                genero TEXT DEFAULT '',
                cep TEXT DEFAULT '',
                endereco TEXT DEFAULT '',
                numero TEXT DEFAULT '',
                complemento TEXT DEFAULT '',
                bairro TEXT DEFAULT '',
                cidade TEXT DEFAULT '',
                uf TEXT DEFAULT '',
                nivel_formacao TEXT DEFAULT '',
                area_atuacao TEXT DEFAULT '',
                linkedin TEXT DEFAULT '',
                aceite_lgpd TEXT DEFAULT ''
            )
            """
        )

    users = read_users()
    if not any(user["cpf"] == "admim" for user in users):
        append_user(
            {
                "cpf": "admim",
                "nome": "Usuário Teste",
                "email": "admim@ifg.edu.br",
                "telefone": "",
                "senha_hash": password_hash("admim"),
                "vinculo": "Colaborador Externo",
                "instituicao": "Polo de Inovação IFG",
                "lattes": "",
                "resumo": "Usuário temporário para testes da área logada.",
                "perfil": "admin",
                "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "aceite_lgpd": "sim",
            }
        )
    else:
        admim = find_user("admim")
        if admim and admim.get("perfil") != "admin":
            update_user("admim", {"perfil": "admin", "vinculo": "Colaborador Externo"})


def read_users() -> list[dict[str, str]]:
    if not DB_FILE.exists():
        return []

    with db_connection() as conn:
        rows = conn.execute("SELECT * FROM usuarios ORDER BY data_cadastro DESC").fetchall()
    return [dict(row) for row in rows]


def append_user(user: dict[str, str]) -> None:
    payload = {field: str(user.get(field, "") or "") for field in USER_FIELDS}
    with db_connection() as conn:
        conn.execute(
            f"""
            INSERT INTO usuarios ({",".join(USER_FIELDS)})
            VALUES ({",".join(["?"] * len(USER_FIELDS))})
            """,
            [payload[field] for field in USER_FIELDS],
        )


def find_user(login: str) -> dict[str, str] | None:
    normalized = login.strip()
    if not normalized or not DB_FILE.exists():
        return None

    with db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE cpf = ? OR lower(email) = lower(?)",
            (normalized, normalized),
        ).fetchone()
    return dict(row) if row else None


def authenticate(login: str, password: str) -> dict[str, str] | None:
    user = find_user(login)
    if user and verify_password(password, user["senha_hash"]):
        return user
    return None


def update_user(cpf: str, values: dict[str, str]) -> dict[str, str] | None:
    allowed = [field for field in values if field in USER_FIELDS and field != "cpf"]
    if not cpf or not allowed:
        return find_user(cpf)

    assignments = ", ".join(f"{field} = ?" for field in allowed)
    params = [str(values.get(field, "") or "") for field in allowed] + [cpf]
    with db_connection() as conn:
        conn.execute(f"UPDATE usuarios SET {assignments} WHERE cpf = ?", params)
    return find_user(cpf)


def users_to_csv() -> str:
    rows = read_users()
    public_fields = [field for field in USER_FIELDS if field != "senha_hash"]
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=public_fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row.get(field, "") for field in public_fields})
    return output.getvalue()


def render_logo() -> None:
    if LOGO_PATH.exists():
        encoded_logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        st.markdown(
            f"""
            <div class="logo-wrap">
                <img src="data:image/png;base64,{encoded_logo}" alt="Instituto Federal Goiás">
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="logo-wrap">
                <strong>Instituto Federal<br>Goiás<br>Polo de Inovação</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


def go_to(page: str) -> None:
    st.session_state.current_page = page
    st.rerun()


def page_login() -> None:
    render_logo()

    if st.session_state.get("flash_message"):
        st.success(st.session_state.pop("flash_message"))

    st.markdown('<p class="hello">Olá!</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="welcome">
            Boas vindas à plataforma do <strong>Banco de Talentos</strong>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login = st.text_input("CPF", placeholder="000.000.000-00")
    password = st.text_input("Senha", type="password")
    st.markdown('<p class="forgot">Esqueceu a senha?</p>', unsafe_allow_html=True)

    left, center, right = st.columns([1, 1.75, 1])
    with center:
        if st.button("Login", type="primary", use_container_width=True):
            user = authenticate(login, password)
            if user:
                st.session_state.authenticated_user = user
                st.session_state.user_menu = "Administração" if user.get("perfil") == "admin" else "Home"
                go_to("area_logada")
            else:
                st.error("CPF/usuário ou senha inválidos.")

    st.markdown(
        '<p class="signup-text">Ainda não se cadastrou?</p>',
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1.15, 1.35, 1.15])
    with center:
        if st.button("Cadastre-se aqui", use_container_width=True):
            st.session_state.public_signup_step = "categoria"
            st.session_state.public_signup_category = None
            go_to("cadastro")


def render_top_menu(default_index: int = 1) -> str:
    if option_menu is not None:
        return option_menu(
            menu_title=None,
            options=["Início", "Cadastro"],
            icons=["house", "person-plus"],
            default_index=default_index,
            orientation="horizontal",
            styles={
                "container": {"padding": "0 0 1rem", "background-color": "transparent"},
                "icon": {"color": GREEN, "font-size": "16px"},
                "nav-link": {
                    "border-radius": "6px",
                    "color": INK,
                    "font-size": "0.95rem",
                    "font-weight": "700",
                    "margin": "0 0.15rem",
                    "padding": "0.7rem 1rem",
                },
                "nav-link-selected": {"background-color": GREEN, "color": "white"},
            },
        )

    return st.segmented_control(
        "Menu",
        ["Início", "Cadastro"],
        default="Cadastro" if default_index == 1 else "Início",
        label_visibility="collapsed",
    )


def set_signup_category(category: str) -> None:
    st.session_state.public_signup_category = category
    st.rerun()


def render_category_option(icon: str, title: str, description: str) -> None:
    selected = st.session_state.get("public_signup_category") == title
    icon_col, text_col = st.columns([0.14, 0.86], vertical_alignment="center")
    with icon_col:
        if st.button(icon, key=f"category_{title}", type="primary" if selected else "secondary", use_container_width=True):
            set_signup_category(title)
    with text_col:
        st.markdown(
            f"""
            <div class="category-copy">
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def page_cadastro_categoria() -> None:
    st.markdown('<div class="signup-flow">', unsafe_allow_html=True)
    st.markdown('<div class="signup-edital">Acesse os editais do Polo de Inovação do IFG</div>', unsafe_allow_html=True)

    if st.button("←", key="signup_back_login"):
        go_to("login")

    st.markdown(
        '<p class="signup-prompt">Agora, selecione qual categoria abaixo você se encaixa:</p>',
        unsafe_allow_html=True,
    )
    render_category_option("♙", "Estudante", "Se você está matriculado em algum curso do IFG ou de outra ICT")
    render_category_option("⌂", "Servidor", "Se você é um servidor público do IFG ou de outra ICT")
    render_category_option("♟", "Colaborador Externo", "Se você já é formado e não é um servidor público")

    left, center, right = st.columns([1, 1.25, 1])
    with center:
        if st.button(
            "Continuar",
            type="primary",
            disabled=not st.session_state.get("public_signup_category"),
            use_container_width=True,
        ):
            st.session_state.public_signup_step = "formulario"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def page_cadastro_formulario() -> None:
    category = st.session_state.get("public_signup_category") or "Servidor"
    st.markdown('<div class="signup-flow">', unsafe_allow_html=True)

    if st.button("←", key="signup_back_category"):
        st.session_state.public_signup_step = "categoria"
        st.rerun()

    st.markdown(
        f'<p class="signup-form-title">Olá {category}, agora só falta você preencher seu cadastro básico!</p>',
        unsafe_allow_html=True,
    )

    nome = st.text_input("Nome Completo*", placeholder="Seu Nome Completo", key="signup_nome")
    email = st.text_input("Email*", placeholder="Seu Email", key="signup_email")
    cpf = st.text_input("CPF*", placeholder="Seu CPF", key="signup_cpf")
    senha = st.text_input(
        "Senha*",
        type="password",
        placeholder="Sua senha de 6 ou mais caracteres",
        key="signup_senha",
    )
    confirmar_senha = st.text_input(
        "Confirmar senha*",
        type="password",
        placeholder="Sua senha de 6 ou mais caracteres",
        key="signup_confirmar_senha",
    )
    aceite_lgpd = st.checkbox(
        "Declaro que li e concordo com o uso dos meus dados para fins de cadastro, seleção e comunicação do Banco de Talentos do Polo de Inovação do IFG.",
        key="signup_aceite_lgpd",
    )

    left, center, right = st.columns([1, 1.35, 1])
    with center:
        submitted = st.button(
            "Cadastrar",
            type="primary",
            disabled=not aceite_lgpd,
            use_container_width=True,
        )

    if submitted:
        required = [cpf, nome, email, senha, confirmar_senha]
        if not all(value.strip() for value in required):
            st.error("Preencha nome, e-mail, CPF e senha.")
        elif len(senha) < 6:
            st.error("A senha precisa ter 6 ou mais caracteres.")
        elif senha != confirmar_senha:
            st.error("A senha e a confirmação de senha precisam ser iguais.")
        elif not aceite_lgpd:
            st.error("É necessário aceitar o termo de uso dos dados para concluir o cadastro.")
        elif find_user(cpf) or find_user(email):
            st.error("Já existe um cadastro com esse CPF ou e-mail.")
        else:
            append_user(
                {
                    "cpf": cpf.strip(),
                    "nome": nome.strip(),
                    "email": email.strip(),
                    "telefone": "",
                    "senha_hash": password_hash(senha),
                    "vinculo": category,
                    "instituicao": "",
                    "lattes": "",
                    "resumo": "",
                    "perfil": "usuario",
                    "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "aceite_lgpd": "sim",
                }
            )
            st.session_state.public_signup_step = "categoria"
            st.session_state.public_signup_category = None
            for key in ["signup_nome", "signup_email", "signup_cpf", "signup_senha", "signup_confirmar_senha", "signup_aceite_lgpd"]:
                st.session_state.pop(key, None)
            st.session_state.flash_message = "Cadastro realizado com sucesso. Faça login para continuar."
            go_to("login")

    st.markdown("</div>", unsafe_allow_html=True)


def page_cadastro() -> None:
    if "public_signup_step" not in st.session_state:
        st.session_state.public_signup_step = "categoria"
    if "public_signup_category" not in st.session_state:
        st.session_state.public_signup_category = None

    if st.session_state.public_signup_step == "formulario":
        page_cadastro_formulario()
    else:
        page_cadastro_categoria()


def logout() -> None:
    st.session_state.pop("authenticated_user", None)
    st.session_state.user_menu = "Home"
    go_to("login")


def render_user_sidebar() -> None:
    user = st.session_state.get("authenticated_user", {})
    name = user.get("nome", "Usuário")
    role = user.get("vinculo", "Colaborador/a Externo/a")
    if role == "Administrador":
        role = "Colaborador/a Externo/a"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-user">
            <strong>{name}</strong>
            <span>{role}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown('<div class="sidebar-nav">', unsafe_allow_html=True)
    if user.get("perfil") == "admin":
        if st.sidebar.button("▣  Administração", key="nav_admin", use_container_width=True):
            st.session_state.user_menu = "Administração"
            st.rerun()
    else:
        if st.sidebar.button("⌂  Home", key="nav_home", use_container_width=True):
            st.session_state.user_menu = "Home"
            st.rerun()
        if st.sidebar.button("◉  Meu Cadastro", key="nav_cadastro", use_container_width=True):
            st.session_state.user_menu = "Meu Cadastro"
            st.rerun()
        if st.sidebar.button("♕  Minha Pontuação", key="nav_pontuacao", use_container_width=True):
            st.session_state.user_menu = "Minha Pontuação"
            st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    st.sidebar.markdown("<div style='height: 34vh;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("↪  Sair", key="nav_sair", use_container_width=True):
        logout()
    st.sidebar.markdown(
        """
        <div class="sidebar-footer">
            <span class="footer-icon">BT</span>
            Banco de Especialistas<br>
            IFG - Polo de Inovação
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_logged_header(content: str) -> None:
    st.markdown(
        f"""
        <div class="app-toolbar">
            <p>{content}</p>
            <span style="color:#6b6b6b;font-size:1.35rem;">&#128276;</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_home(user: dict[str, str]) -> None:
    render_logged_header("Olá! Boas vindas à plataforma do <strong>Banco de Especialistas</strong>")
    st.markdown(
        """
        <div class="workspace">
            <div class="hero-art">
                <div class="art-blob"></div>
                <div class="art-blob two"></div>
                <div class="screen"></div>
                <div class="desk"></div>
                <div class="globe"></div>
                <div class="person"></div>
                <div class="ground"></div>
            </div>
            <div>
                <div class="action-card">
                    <span>&#128462; Sua inscrição</span>
                    <span style="background:#d8d8d8;border-radius:50%;padding:.25rem .55rem;">?</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tab_class(tab: str, current: str) -> str:
    if tab == current and tab != "Dados Pessoais":
        return "active"
    if tab == "Dados Pessoais":
        return "done"
    return "muted"


def render_cadastro_tabs(current: str) -> None:
    col1, col2, col3, spacer = st.columns([1, 1, 1, 1.35])
    with col1:
        if st.button(
            "👤  DADOS PESSOAIS ✓",
            key="tab_dados",
            type="primary" if current == "Dados Pessoais" else "secondary",
            use_container_width=True,
        ):
            st.session_state.cadastro_tab = "Dados Pessoais"
            st.rerun()
    with col2:
        if st.button(
            "⌂  ENDEREÇO",
            key="tab_endereco",
            type="primary" if current == "Endereço" else "secondary",
            use_container_width=True,
        ):
            st.session_state.cadastro_tab = "Endereço"
            st.rerun()
    with col3:
        if st.button(
            "▰  FORMAÇÃO",
            key="tab_formacao",
            type="primary" if current == "Formação" else "secondary",
            use_container_width=True,
        ):
            st.session_state.cadastro_tab = "Formação"
            st.rerun()


def cadastro_tab_selector() -> str:
    options = ["Dados Pessoais", "Endereço", "Formação"]
    current = st.session_state.get("cadastro_tab", "Dados Pessoais")
    if current not in options:
        current = "Dados Pessoais"

    render_cadastro_tabs(current)
    return st.session_state.get("cadastro_tab", current)


def save_registration_notice(user: dict[str, str], values: dict[str, str]) -> None:
    st.markdown('<div class="save-divider"></div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1])
    with left:
        if st.button("Voltar", use_container_width=True):
            st.session_state.user_menu = "Home"
            st.rerun()
    with right:
        if st.button("Salvar", type="primary", use_container_width=True):
            updated = update_user(user.get("cpf", ""), values)
            if updated:
                st.session_state.authenticated_user = updated
                st.success("Dados salvos com sucesso.")
            else:
                st.error("Não foi possível salvar os dados deste cadastro.")


def page_dados_pessoais(user: dict[str, str]) -> None:
    col1, col2, col3 = st.columns([2.1, 1, 1])
    with col1:
        nome = st.text_input("Nome Completo", value=user.get("nome", ""))
    with col2:
        st.text_input("CPF", value=user.get("cpf", ""), disabled=True)
    with col3:
        data_nascimento = st.text_input("Data de Nascimento", value=user.get("data_nascimento", ""), placeholder="dd/mm/aaaa")

    col4, col5 = st.columns(2)
    with col4:
        rg = st.text_input("RG", value=user.get("rg", ""))
    with col5:
        orgao_emissor = st.text_input("Orgão Emissor", value=user.get("orgao_emissor", ""))

    col6, col7 = st.columns(2)
    with col6:
        telefone = st.text_input("Telefone", value=user.get("telefone", ""))
    with col7:
        email = st.text_input("Email", value=user.get("email", ""))

    col8, _ = st.columns([1, 1])
    with col8:
        generos = ["Selecione", "Feminino", "Masculino", "Prefiro não informar", "Outro"]
        genero_atual = user.get("genero", "Selecione")
        genero = st.selectbox(
            "Gênero",
            generos,
            index=generos.index(genero_atual) if genero_atual in generos else 0,
        )

    save_registration_notice(
        user,
        {
            "nome": nome,
            "data_nascimento": data_nascimento,
            "rg": rg,
            "orgao_emissor": orgao_emissor,
            "telefone": telefone,
            "email": email,
            "genero": "" if genero == "Selecione" else genero,
        },
    )


def page_endereco(user: dict[str, str]) -> None:
    col1, _ = st.columns([1, 1])
    with col1:
        cep = st.text_input("CEP", value=user.get("cep", ""))

    col3, col4, col5 = st.columns([2, 1, 1])
    with col3:
        endereco = st.text_input("Endereço", value=user.get("endereco", ""))
    with col4:
        numero = st.text_input("Nº", value=user.get("numero", ""))
    with col5:
        complemento = st.text_input("Complemento (Opcional)", value=user.get("complemento", ""))

    col6, col7, col8 = st.columns([2, 1.3, .6])
    with col6:
        bairro = st.text_input("Bairro", value=user.get("bairro", ""))
    with col7:
        cidade = st.text_input("Cidade", value=user.get("cidade", ""))
    with col8:
        uf = st.text_input("UF", value=user.get("uf", ""))

    save_registration_notice(
        user,
        {
            "cep": cep,
            "endereco": endereco,
            "numero": numero,
            "complemento": complemento,
            "bairro": bairro,
            "cidade": cidade,
            "uf": uf,
        },
    )


def page_formacao(user: dict[str, str]) -> None:
    col1, col2 = st.columns(2)
    with col1:
        nivel_atual = user.get("nivel_formacao", FORMACAO_NIVEIS[0])
        nivel_formacao = st.selectbox(
            "Nível de Formação",
            FORMACAO_NIVEIS,
            index=FORMACAO_NIVEIS.index(nivel_atual) if nivel_atual in FORMACAO_NIVEIS else 0,
        )
    with col2:
        area_atual = user.get("area_atuacao", CNPQ_AREAS[0])
        area_atuacao = st.selectbox(
            "Área de Atuação",
            CNPQ_AREAS,
            index=CNPQ_AREAS.index(area_atual) if area_atual in CNPQ_AREAS else 0,
        )

    col3, col4 = st.columns(2)
    with col3:
        lattes = st.text_input("Currículo Lattes", value=user.get("lattes", ""))
    with col4:
        linkedin = st.text_input("Linkedin", value=user.get("linkedin", ""))

    save_registration_notice(
        user,
        {
            "nivel_formacao": nivel_formacao,
            "area_atuacao": area_atuacao,
            "lattes": lattes,
            "linkedin": linkedin,
        },
    )


def page_meu_cadastro(user: dict[str, str]) -> None:
    render_logged_header("Meu Cadastro &gt; <strong>Formulário de Cadastro</strong>")
    st.markdown('<div class="registration-page">', unsafe_allow_html=True)

    left, right = st.columns([1, .25])
    with left:
        st.markdown("<h2 style='font-size:1.35rem;margin:0 0 .55rem;color:#202124;'>Meu Cadastro</h2>", unsafe_allow_html=True)
    with right:
        if st.button("← Voltar", key="cadastro_voltar_top", use_container_width=True):
            st.session_state.user_menu = "Home"
            st.rerun()

    active_tab = cadastro_tab_selector()

    if active_tab == "Endereço":
        page_endereco(user)
    elif active_tab == "Formação":
        page_formacao(user)
    else:
        page_dados_pessoais(user)

    st.markdown("</div>", unsafe_allow_html=True)


def page_minha_pontuacao(user: dict[str, str]) -> None:
    render_logged_header("Minha Pontuação &gt; <strong>Resumo da Avaliação</strong>")
    st.markdown('<p class="section-title">Minha Pontuação</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="placeholder-card">
            <p style="margin:0;color:#575757;">
                A pontuação ainda não foi configurada. Na próxima etapa podemos criar a tela
                com os critérios do edital e o status da avaliação.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_administracao(user: dict[str, str]) -> None:
    if user.get("perfil") != "admin":
        st.session_state.user_menu = "Home"
        st.rerun()

    render_logged_header("Administração &gt; <strong>Cadastros recebidos</strong>")
    users = read_users()
    public_fields = [field for field in USER_FIELDS if field != "senha_hash"]
    rows = [{field: item.get(field, "") for field in public_fields} for item in users]

    total = len(rows)
    completos = sum(1 for row in rows if row.get("nivel_formacao") and row.get("cep"))
    st.markdown(
        f"""
        <div class="placeholder-card">
            <p style="margin:0;"><strong>{total}</strong> cadastro(s) recebido(s) · <strong>{completos}</strong> com endereço e formação preenchidos</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.download_button(
        "Baixar cadastros em CSV",
        users_to_csv().encode("utf-8-sig"),
        "cadastros_banco_talentos_ifg.csv",
        "text/csv",
        use_container_width=True,
    )


def page_area_logada() -> None:
    user = st.session_state.get("authenticated_user")
    if not user:
        go_to("login")

    render_user_sidebar()
    active = st.session_state.get("user_menu", "Home")
    if user.get("perfil") == "admin":
        active = "Administração"
        st.session_state.user_menu = active

    if active == "Meu Cadastro":
        page_meu_cadastro(user)
    elif active == "Minha Pontuação":
        page_minha_pontuacao(user)
    elif active == "Administração":
        page_administracao(user)
    else:
        page_home(user)


def main() -> None:
    ensure_users_file()

    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"
    if "user_menu" not in st.session_state:
        st.session_state.user_menu = "Home"

    show_sidebar = st.session_state.current_page == "area_logada"
    inject_css(show_sidebar=show_sidebar)

    if st.session_state.current_page == "cadastro":
        page_cadastro()
    elif st.session_state.current_page == "area_logada":
        page_area_logada()
    else:
        page_login()


if __name__ == "__main__":
    main()
